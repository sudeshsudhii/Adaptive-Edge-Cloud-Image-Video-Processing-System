# cloud/aws_provider.py
"""AWS EC2 + S3 cloud provider (boto3)."""

from __future__ import annotations

import time
from typing import Optional

from backend.config import settings
from backend.models import CloudResponse
from observability.logger import get_logger

logger = get_logger("aws")


class AWSProvider:
    """Real AWS operations via boto3."""

    def __init__(self) -> None:
        import boto3
        self.ec2 = boto3.client("ec2", region_name=settings.AWS_REGION)
        self.s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        self.asg = boto3.client("autoscaling", region_name=settings.AWS_REGION)
        self.instance_type = settings.AWS_EC2_INSTANCE_TYPE
        logger.info(f"AWSProvider initialised (region={settings.AWS_REGION})")

    def process(self, input_path: str, operation: str) -> CloudResponse:
        """
        In a real deployment this would:
        1. Upload input to S3
        2. Trigger an EC2 instance / Lambda to process
        3. Download result
        For now, this is the boto3 skeleton.
        """
        start = time.time()
        key = f"inputs/{input_path.split('/')[-1]}"
        self.s3.upload_file(input_path, settings.AWS_S3_BUCKET, key)
        # In production: trigger processing on EC2 / Lambda
        elapsed = time.time() - start
        return CloudResponse(
            provider="aws",
            instance_id="i-placeholder",
            processing_time_s=elapsed,
            cost_usd=elapsed * 0.0000125,
            output_path=f"s3://{settings.AWS_S3_BUCKET}/outputs/{key}",
        )

    def scale_up(self, desired: int) -> None:
        logger.info(f"AWS scale_up: desired={desired} instances")
        # self.asg.set_desired_capacity(...)

    def scale_down(self, desired: int) -> None:
        logger.info(f"AWS scale_down: desired={desired} instances")
