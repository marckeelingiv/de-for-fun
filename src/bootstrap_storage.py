import os
import sys
from minio import Minio
from minio.error import S3Error

def main():
    print("=== Bootstrapping MinIO Storage ===")
    
    # Retrieve MinIO settings from env, stripping protocols for the Minio client constructor
    raw_endpoint = os.environ.get("MINIO_ENDPOINT", "localhost:9000")
    endpoint = raw_endpoint.replace("http://", "").replace("https://", "")
    access_key = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    
    print(f"Connecting to MinIO at {raw_endpoint}...")
    
    try:
        # Initialize MinIO client
        client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False
        )
        
        # Verify and create bucket
        bucket_name = "data-lakehouse"
        if not client.bucket_exists(bucket_name):
            print(f"Bucket '{bucket_name}' does not exist. Creating...")
            client.make_bucket(bucket_name)
            print(f"Bucket '{bucket_name}' created successfully!")
        else:
            print(f"Bucket '{bucket_name}' already exists.")
            
        print("=== MinIO Bootstrapping Complete ===")
    except S3Error as err:
        print(f"MinIO S3 Error: {err}")
        sys.exit(1)
    except Exception as err:
        print(f"Error connecting to MinIO: {err}")
        sys.exit(1)

if __name__ == "__main__":
    main()
