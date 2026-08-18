import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from minio import Minio
from minio.deleteobjects import DeleteObject

from src.config import MinIOConfig


def main() -> None:
    prefix = sys.argv[1] if len(sys.argv) > 1 else "analytics/"
    cfg = MinIOConfig.from_env()
    client = Minio(
        cfg.endpoint,
        access_key=cfg.access_key,
        secret_key=cfg.secret_key,
        secure=cfg.secure,
    )
    objects = list(client.list_objects(cfg.bucket, prefix=prefix, recursive=True))
    if not objects:
        print(f"No objects found under s3://{cfg.bucket}/{prefix}")
        return
    errors = list(client.remove_objects(cfg.bucket, [DeleteObject(obj.object_name) for obj in objects]))
    for error in errors:
        print(f"Failed to delete {error.object_name}: {error}", file=sys.stderr)
    if errors:
        raise SystemExit(1)
    print(f"Deleted {len(objects)} objects under s3://{cfg.bucket}/{prefix}")


if __name__ == "__main__":
    main()
