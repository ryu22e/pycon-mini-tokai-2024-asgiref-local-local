import threading
import asyncio
import uuid


local_storage = threading.local()


async def test_task(wait):
    start_request_id = uuid.uuid4().hex
    thread_id = threading.get_ident()
    local_storage.request_id = start_request_id

    # local_storageがコルーチンごとに独立していない場合、ここで待機中に別のコルーチンでlocal_storage.request_idを上書きしてしまう場合がある。
    await asyncio.sleep(wait)

    end_request_id = getattr(local_storage, "request_id", None)
    equal_or_not = "==" if start_request_id == end_request_id else "!="
    print(f"{thread_id=} ({start_request_id=}) {equal_or_not} ({end_request_id=})")


async def main():
    tasks = (
        test_task(3),
        test_task(2),
        test_task(1),
    )
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
