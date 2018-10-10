import json
from base64 import b64decode
from urllib.request import urlopen

from django.core.mail import mail_admins
from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from M2Crypto import X509
from M2Crypto.Err import M2CryptoError

from .models import EncodeJob
from .signals import transcode_oncomplete, transcode_onerror, transcode_onprogress

SNS_MESSAGE_TYPE_SUB_NOTIFICATION = "SubscriptionConfirmation"
SNS_MESSAGE_TYPE_NOTIFICATION = "Notification"
SNS_MESSAGE_TYPE_UNSUB_NOTIFICATION = "UnsubscribeConfirmation"


def canonical_message_builder(content, format):
    """ 
    Builds the canonical message to be verified.
    Sorts the fields as a requirement from AWS
    Args:
        content (dict): Parsed body of the response
        format (list): List of the fields that need to go into the message
    Returns (str):
        canonical message
    """
    m = ""

    for field in sorted(format):
        try:
            m += field + "\n" + content[field] + "\n"
        except KeyError:
            # Build with what you have
            pass

    return str(m).encode()


def verify_sns_notification(request, content):
    """ 
    Takes a notification request from Amazon push service SNS and verifies the origin of the notification.
    Kudos to Artur Rodrigues for suggesting M2Crypto: http://goo.gl/KAgPPc
    Args:
        request (HTTPRequest): The request object that is passed to the view function
    Returns (bool):
        True if he message passes the verification, False otherwise
    Raises:
        ValueError: If the body of the response couldn't be parsed
        M2CryptoError: If an error raises during the verification process
        URLError: If the SigningCertURL couldn't be opened
    """
    cert = None
    pubkey = None
    canonical_message = None
    canonical_sub_unsub_format = [
        "Message",
        "MessageId",
        "SubscribeURL",
        "Timestamp",
        "Token",
        "TopicArn",
        "Type",
    ]
    canonical_notification_format = [
        "Message",
        "MessageId",
        "Subject",
        "Timestamp",
        "TopicArn",
        "Type",
    ]

    decoded_signature = b64decode(content["Signature"])

    # Depending on the message type, the canonical message format varies: http://goo.gl/oSrJl8
    if (
        request.META.get("HTTP_X_AMZ_SNS_MESSAGE_TYPE", None)
        == SNS_MESSAGE_TYPE_SUB_NOTIFICATION
        or request.META.get("HTTP_X_AMZ_SNS_MESSAGE_TYPE", None)
        == SNS_MESSAGE_TYPE_UNSUB_NOTIFICATION
    ):

        canonical_message = canonical_message_builder(
            content, canonical_sub_unsub_format
        )

    elif (
        request.META.get("HTTP_X_AMZ_SNS_MESSAGE_TYPE", None)
        == SNS_MESSAGE_TYPE_NOTIFICATION
    ):

        canonical_message = canonical_message_builder(
            content, canonical_notification_format
        )

    else:
        raise ValueError(
            "Message Type (%s) is not recognized"
            % request.META.get("HTTP_X_AMZ_SNS_MESSAGE_TYPE", None)
        )

    # Load the certificate and extract the public key
    cert = X509.load_cert_string(
        urlopen(content["SigningCertURL"]).read().decode("utf-8")
    )
    pubkey = cert.get_pubkey()
    pubkey.reset_context(md="sha1")
    pubkey.verify_init()

    # Feed the canonical message to sign it with the public key from the certificate
    pubkey.verify_update(canonical_message)

    # M2Crypto uses EVP_VerifyFinal() from openssl as the underlying verification function.
    # http://goo.gl/Bk2G36: "EVP_VerifyFinal() returns 1 for a correct signature, 0 for failure and -1
    # if some other error occurred."
    verification_result = pubkey.verify_final(decoded_signature)

    if verification_result == 1:
        return True
    elif verification_result == 0:
        return False
    else:
        raise M2CryptoError("Some error occured while verifying the signature.")


@csrf_exempt
@require_http_methods(["POST"])
def endpoint(request):
    """
    Receive SNS notification
    """
    data = {}
    try:
        data = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest(str(e))

    try:
        if not verify_sns_notification(request, data):
            return HttpResponseBadRequest(
                "Unable to verify authenticity of SNS notification."
            )
    except (ValueError, M2CryptoError) as e:
        return HttpResponseBadRequest(str(e))

    # Handle the SNS subscription
    if (
        request.META.get("HTTP_X_AMZ_SNS_MESSAGE_TYPE", None)
        == SNS_MESSAGE_TYPE_SUB_NOTIFICATION
    ):
        subscribe_topic = data["TopicArn"]
        subscribe_url = data["SubscribeURL"]
        subscribe_body = """
        Automatically confirming subscription to topic: %s

        %s """ % (
            subscribe_topic,
            subscribe_url,
        )

        mail_admins("SNS Subscription Automatically Confirmed", subscribe_body)
        response = urlopen(subscribe_url)
        return HttpResponse(response.read().decode("utf-8"))

    try:
        message = json.loads(data["Message"])
    except ValueError:
        assert False, data["Message"]

    try:
        # Turn the dictionary into a readable string format
        formatted_str_message = json.dumps(message, indent=2)
    except (TypeError, ValueError):
        # Couldn't format it, so set it to the raw message
        formatted_str_message = data["Message"]

    if message["state"] == "PROGRESSING":
        job = EncodeJob.objects.get(pk=message["jobId"])
        job.message = "Progress"
        job.state = 1
        job.save()

        transcode_onprogress.send(sender=None, job=job, message=message)
    elif message["state"] == "COMPLETED":
        job = EncodeJob.objects.get(pk=message["jobId"])
        job.message = "Success"
        job.state = 4
        job.save()

        transcode_oncomplete.send(sender=None, job=job, message=message)
    elif message["state"] == "ERROR":
        job = EncodeJob.objects.get(pk=message["jobId"])
        # add the entire message dictionary for easier debugging
        job.message = formatted_str_message
        job.state = 2
        job.save()

        transcode_onerror.send(sender=None, job=job, message=message)

    return HttpResponse("Done")
