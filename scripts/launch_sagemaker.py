"""Submit an sklearn script-mode training job with IAM role credentials."""

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training-s3-uri", required=True)
    parser.add_argument("--role-arn", default=os.getenv("AWS_ROLE_ARN"))
    parser.add_argument("--instance-type", default="ml.m5.large")
    args = parser.parse_args()
    if not args.role_arn or not args.training_s3_uri.startswith("s3://"):
        parser.error("Provide an IAM role ARN and an S3 training prefix")
    from sagemaker.sklearn.estimator import SKLearn
    estimator = SKLearn(entry_point="train.py", source_dir="src/service", role=args.role_arn,
                        framework_version="1.4-2", py_version="py3", instance_count=1,
                        instance_type=args.instance_type, max_run=3600,
                        volume_size=30, output_path=os.getenv("SM_OUTPUT_S3_URI"))
    estimator.fit({"train": args.training_s3_uri}, wait=True)
    print(estimator.model_data)


if __name__ == "__main__":
    main()
