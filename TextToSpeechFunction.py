import logging
import os
from urllib.parse import unquote_plus

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")
polly = boto3.client("polly")

SOURCE_BUCKET = os.environ.get(
    "SOURCE_BUCKET", "amc-polly-source-bucket-gow"
)
DESTINATION_BUCKET = os.environ.get(
    "DESTINATION_BUCKET", "gow-polly-destination-bucket-g"
)
VOICE_ID = os.environ.get("POLLY_VOICE_ID", "Joanna")


def lambda_handler(event, context):
    for record in event.get("Records", []):
        if not record.get("eventName", "").startswith("ObjectCreated:"):
            continue

        source_bucket = record["s3"]["bucket"]["name"]
        source_key = unquote_plus(record["s3"]["object"]["key"])

        if source_key.lower().endswith(".txt"):
            try:
                if source_bucket != SOURCE_BUCKET:
                    raise ValueError(
                        f"Unexpected source bucket: {source_bucket}"
                    )

                response = s3.get_object(Bucket=source_bucket, Key=source_key)
                with response["Body"] as body:
                    text = body.read().decode("utf-8")

                audio_response = polly.synthesize_speech(
                    Text=text,
                    OutputFormat="mp3",
                    VoiceId=VOICE_ID,
                )
                with audio_response["AudioStream"] as audio_stream:
                    audio = audio_stream.read()

                output_key = f"audio/{source_key[:-4]}.mp3"
                s3.put_object(
                    Bucket=DESTINATION_BUCKET,
                    Key=output_key,
                    Body=audio,
                    ContentType="audio/mpeg",
                )
                logger.info(
                    "Saved synthesized audio to s3://%s/%s",
                    DESTINATION_BUCKET,
                    output_key,
                )
            except Exception:
                logger.exception(
                    "Failed to synthesize s3://%s/%s",
                    source_bucket,
                    source_key,
                )
                raise
