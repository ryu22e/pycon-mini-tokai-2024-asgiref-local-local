# asgirefのクラスasgiref.local.Localは何のためにあるのか？

<a rel="license" href="http://creativecommons.org/licenses/by/4.0/"><img alt="Creative Commons License" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a>
<small>This work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International License</a>.</small>

## はじめに

### 自己紹介

* Ryuji Tsutsui@ryu22e
* さくらインターネット株式会社所属
* Python歴は13年くらい（主にDjango）
* Python Boot Camp、Shonan.py、GCPUG Shonanなどコミュニティ活動もしています
* 著書（共著）：『[Python実践レシピ](https://gihyo.jp/book/2022/978-4-297-12576-9)』

### このトークで話すこと

* asgirefというPythonパッケージの話
* とりわけ、asgiref.local.Localというクラスについての解説

### このトークの対象者

* マルチスレッド、コルーチンなど非同期処理の知識がある人
* なんとなく知っていればOK

### このトークで得られること

* asgirefの概要
* asgiref.local.Localの用途、存在する理由

### このトークの構成

* asgirefとは何か
* asgiref.local.Localとは何か
* asgiref.local.Localとthreading.localの違い
* asgiref.local.Localとcontextvars.ContextVarの違い

## asgirefとは何か

### asgirefの概要

* ASGIアプリケーション（非同期処理を行うアプリケーション）を開発しやすくするPythonライブラリ
* Djangoコミュニティが開発している

### asgirefに依存しているツール、フレームワーク

* Daphne
* Django
* Connexion

### 参考資料

以下のドキュメントにasgirefを使ったツール、フレームワークのリストがある。

[asgiref/docs/implementations.rst at main · django/asgiref](https://github.com/django/asgiref/blob/main/docs/implementations.rst)

ただし、バージョンが上がってasgirefに依存しなくなったものも載っている。

### asgirefの主な機能

* 同期処理から非同期処理への変換（`sync_to_async()`）
* 非同期処理から同期処理への変換（`async_to_sync()`）
* ローカルストレージ（asgiref.local.Local）
* サーバーの基本機能
* WSGIからASGIへのアダプター

```{revealjs-break}
```

特に一番上の`sync_to_async()`はDjangoの非同期ビューを使う際はお世話になる。

### Djangoで`sync_to_async()`が必要になるケース

* Djangoでは非同期ビューがサポートされている（3.1から）
* 非同期ビューの中では同期処理を呼べない（呼ぶとエラーになる仕組み）
* とはいえ、Djangoの機能には非同期サポートしていないものもある
* そこで、`sync_to_async()`で同期処理を非同期処理に変換する

### `sync_to_async()`の使い方

```{revealjs-code-block} python

>>> from asgiref.sync import sync_to_async
>>> # 同期処理の関数を引数として渡すと非同期関数に変換される
>>> results = await sync_to_async(sync_function)
>>> # 関数デコレータとしても使える
>>> @sync_to_async
>>> def sync_function(): ...
```

### 今回のトークの主役は`sync_to_async()`ではなくasgiref.local.LocaL

実際にasgiref.local.Localを使って役立った体験が本トークのモチベーションなので、今日はasgiref.local.Localの話をします。

## asgiref.local.Localとは何か

### docstringによると

> Local storage for async tasks.

非同期タスク用のローカルストレージ

### 私がこのクラスを使った経緯

* DjangoアプリケーションのログにリクエストごとにユニークなIDを付与したかった
* ミドルウェアで `uuid.uuid4()` で生成したIDを設定し、ロギングフィルターで取得するつもりだった
* ところが、ミドルウェアで設定した値をロギングフィルターで取得する方法が見当たらなかった

### 参考にしたOSS

[django-log-request-id](https://pypi.org/project/django-log-request-id/)を参考にした。

### django-log-request-idのミドルウェアの実装（一部抜粋）

```{revealjs-code-block} python

# （省略）
class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request_id = self._get_request_id(request)
        local.request_id = request_id  # ここに注目
# （省略）
```

<https://github.com/dabapps/django-log-request-id/blob/2.1.0/log_request_id/middleware.py>

### django-log-request-idのロギングフィルターの実装（一部抜粋）

```{revealjs-code-block} python

# （省略）
class RequestIDFilter(logging.Filter):

    def filter(self, record):
        default_request_id = getattr(settings, LOG_REQUESTS_NO_SETTING, DEFAULT_NO_REQUEST_ID)
        # ↓ここに注目
        record.request_id = getattr(local, 'request_id', default_request_id)
        return True
```

<https://github.com/dabapps/django-log-request-id/blob/2.1.0/log_request_id/filters.py>

### django-log-request-idのlocal変数の定義（一部抜粋）

```{revealjs-code-block} python
import threading

__version__ = "2.1.0"


try:
    from asgiref.local import Local  # ここに注目
except ImportError:
    from threading import local as Local  # ここにも注目


local = Local()
# （省略）
```

<https://github.com/dabapps/django-log-request-id/blob/2.1.0/log_request_id/__init__.py>

### asgiref.local.Localとthreading.local

* どうやら、両者は似たようなものっぽい
* どこが違うのだろうか？

## asgiref.local.Localとthreading.localの違い

### threading.localとは

* threadingは標準モジュール
* threading.localは、スレッドごとに固有のローカルストレージ

### threading.localのサンプルコード（マルチスレッド）

```{revealjs-code-block} python
import uuid
import time
import threading
from threading import local

local_storage = local()

def test_task(wait):
    # スレッドID取得
    thread_id = threading.get_ident()

    # 1. ユニークIDをローカルストレージに設定
    start_unique_id = uuid.uuid4().hex
    local_storage.unique_id = start_unique_id

    # 2. wait秒待つ
    time.sleep(wait)

    # 3. wait秒待機後のユニークIDを取得
    # （他のスレッドが値を上書きしていないはず）
    end_unique_id = getattr(local_storage, "unique_id", None)
    equal_or_not = "==" if start_unique_id == end_unique_id else "!="
    print(f"{thread_id=} ({start_unique_id=}) {equal_or_not} ({end_unique_id=})")

def main():
    # 待機時間が異なるスレッドを3つ立ち上げる
    threads = [
        threading.Thread(target=test_task, args=(3,)),
        threading.Thread(target=test_task, args=(2,)),
        threading.Thread(target=test_task, args=(1,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-threading-local-multithreads-py>

### threading.localのサンプルコード（マルチスレッド）実行結果

`threading.local`に入れたユニークIDがスレッドごとに異なることがわかる。

```{revealjs-code-block} shell
thread_id=6173028352 (start_unique_id='0863e8995b064f3e9c24ed1dbe926577') == (end_unique_id='0863e8995b064f3e9c24ed1dbe926577')
thread_id=6156201984 (start_unique_id='0fe21b299ab34f7e83fb979277ccce3a') == (end_unique_id='0fe21b299ab34f7e83fb979277ccce3a')
thread_id=6139375616 (start_unique_id='2e7e9d7b8b59439dbd73fc826e45cc32') == (end_unique_id='2e7e9d7b8b59439dbd73fc826e45cc32')
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-threading-local-multithreads-md>

### もし、threading.local以外のオブジェクトを使ったら

```{revealjs-code-block} python
import uuid
import time
import threading

# もし、threading.local以外のオブジェクトを使ったら
class LocalStorage: ...

local_storage = LocalStorage()

def test_task(wait):
    # スレッドID取得
    thread_id = threading.get_ident()

    # 1. ユニークIDをローカルストレージに設定
    start_unique_id = uuid.uuid4().hex
    local_storage.unique_id = start_unique_id

    # 2. wait秒待つ
    time.sleep(wait)

    # 3. wait秒待機後のユニークIDを取得
    # （他のスレッドが値を上書きしていないはず）
    end_unique_id = getattr(local_storage, "unique_id", None)
    equal_or_not = "==" if start_unique_id == end_unique_id else "!="
    print(f"{thread_id=} ({start_unique_id=}) {equal_or_not} ({end_unique_id=})")

def main():
    # 待機時間が異なるスレッドを3つ立ち上げる
    threads = [
        threading.Thread(target=test_task, args=(3,)),
        threading.Thread(target=test_task, args=(2,)),
        threading.Thread(target=test_task, args=(1,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-threading-local-multithreads2-py>

### 実行結果

`local_storage`はすべてのスレッドで共有のオブジェクトになっている。

```{revealjs-code-block} shell
thread_id=6187102208 (start_unique_id='512dffda46f44e6bbd12c01bba4d4f3c') == (end_unique_id='512dffda46f44e6bbd12c01bba4d4f3c')
thread_id=6170275840 (start_unique_id='0f5912e47aee412f9342c2e49bf96d2c') != (end_unique_id='512dffda46f44e6bbd12c01bba4d4f3c')
thread_id=6153449472 (start_unique_id='b1587085778e49f789fc02fb73f1ce9b') != (end_unique_id='512dffda46f44e6bbd12c01bba4d4f3c')
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-threading-local-multithreads2-md>

### threading.localの弱点

* コルーチンを使ったコードではthreading.localを使えない
* なぜなら、コルーチンはシングルスレッドで複数のタスクを処理するため、スレッドごとのローカルストレージが使えない

### threading.localのサンプルコード（コルーチン）

```{revealjs-code-block} python
import threading
import asyncio
import uuid

local_storage = threading.local()

async def test_task(wait):
    start_unique_id = uuid.uuid4().hex

    thread_id = threading.get_ident()
    local_storage.unique_id = start_unique_id

    # ここで待機中に別のコルーチンでlocal_storage.unique_idを上書きしてしまう場合がある。
    await asyncio.sleep(wait)

    end_unique_id = getattr(local_storage, "unique_id", None)
    equal_or_not = "==" if start_unique_id == end_unique_id else "!="
    print(f"{thread_id=} ({start_unique_id=}) {equal_or_not} ({end_unique_id=})")

async def main():
    tasks = (
        test_task(3),
        test_task(2),
        test_task(1),
    )
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-threading-local-co-routine-py>

### threading.localのサンプルコード（コルーチン）実行結果

`wait`秒待機中に他のコルーチンが`local_storage.unique_id`を上書きしてしまうことがある。

```{revealjs-code-block} shell
thread_id=8370802496 (start_unique_id='b8e9a1f3e8714831b2aa8275fa47b8f1') == (end_unique_id='b8e9a1f3e8714831b2aa8275fa47b8f1')
thread_id=8370802496 (start_unique_id='cdd46248fbe44f57a2a488919add7d1e') != (end_unique_id='b8e9a1f3e8714831b2aa8275fa47b8f1')
thread_id=8370802496 (start_unique_id='39eb437c91e8437dae500b91e36bb3ff') != (end_unique_id='b8e9a1f3e8714831b2aa8275fa47b8f1')
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-threading-local-co-routine-md>

### PythonのWebアプリケーションは、マルチスレッド、コルーチンの両方を使うことがある

マルチスレッド、コルーチンの両方で使えるローカルストレージがあると便利

### そこで`asgiref.local.Local`クラスの登場

`asgiref.local.Local`は、マルチスレッド、コルーチンの両方で使えるローカルストレージ

### asgiref.local.Localのサンプルコード（マルチスレッド）

```{revealjs-code-block} python
import uuid
import time
import threading

from asgiref.local import Local

local_storage = Local()  # ここを変えただけ

def test_task(wait):
    # スレッドID取得
    thread_id = threading.get_ident()

    # 1. ユニークIDをローカルストレージに設定
    start_unique_id = uuid.uuid4().hex
    local_storage.unique_id = start_unique_id

    # 2. wait秒待つ
    time.sleep(wait)

    # 3. wait秒待機後のユニークIDを取得
    # （他のスレッドが値を上書きしていないはず）
    end_unique_id = getattr(local_storage, "unique_id", None)
    equal_or_not = "==" if start_unique_id == end_unique_id else "!="
    print(f"{thread_id=} ({start_unique_id=}) {equal_or_not} ({end_unique_id=})")

def main():
    # 待機時間が異なるスレッドを3つ立ち上げる
    threads = [
        threading.Thread(target=test_task, args=(3,)),
        threading.Thread(target=test_task, args=(2,)),
        threading.Thread(target=test_task, args=(1,)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-asgiref-local-local-multithreads-py>

### asgiref.local.Localのサンプルコード（マルチスレッド）実行結果

threading.localと同じく、`asgiref.local.Local`に入れたユニークIDがスレッドごとに異なることがわかる。

```{revealjs-code-block} shell
thread_id=6140276736 (start_unique_id='43faa0bb3add4921b1e2649af269646e') == (end_unique_id='43faa0bb3add4921b1e2649af269646e')
thread_id=6123450368 (start_unique_id='d244e874e5f74940a944895c641302c3') == (end_unique_id='d244e874e5f74940a944895c641302c3')
thread_id=6106624000 (start_unique_id='4ed999ac3ad04dbaafa26eda3ad71a0b') == (end_unique_id='4ed999ac3ad04dbaafa26eda3ad71a0b')
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-asgiref-local-local-multithreads-md>

### asgiref.local.Localのサンプルコード（コルーチン）

```{revealjs-code-block} python
import threading
import asyncio
import uuid

from asgiref.local import Local

local_storage = Local()  # ここを変えただけ

async def test_task(wait):
    # スレッドID取得
    thread_id = threading.get_ident()

    # 1. ユニークIDをローカルストレージに設定
    start_unique_id = uuid.uuid4().hex
    local_storage.unique_id = start_unique_id

    # 2. wait秒待つ
    await asyncio.sleep(wait)

    # 3. wait秒待機後のユニークIDを取得
    end_unique_id = getattr(local_storage, "unique_id", None)
    equal_or_not = "==" if start_unique_id == end_unique_id else "!="
    print(f"{thread_id=} ({start_unique_id=}) {equal_or_not} ({end_unique_id=})")

async def main():
    tasks = (
        test_task(3),
        test_task(2),
        test_task(1),
    )
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-asgiref-local-local-co-routine-py>

### asgiref.local.Localのサンプルコード（コルーチン）実行結果

コルーチンごとに固有のローカルストレージが使えることがわかる。

```{revealjs-code-block} shell
thread_id=8323698496 (start_unique_id='9484892561164a18af996c2cf7ab6c2f') == (end_unique_id='9484892561164a18af996c2cf7ab6c2f')
thread_id=8323698496 (start_unique_id='2f7b73f1301648f3a6cf4a8b2d29f559') == (end_unique_id='2f7b73f1301648f3a6cf4a8b2d29f559')
thread_id=8323698496 (start_unique_id='9fc06c8056184fc88c1f3af56e77330d') == (end_unique_id='9fc06c8056184fc88c1f3af56e77330d')
```

### ここまでのまとめ

* threading.localはスレッドごとに固有のローカルストレージ
* ただし、コルーチンはシングルスレッドなのでthreading.localは使えない
* asgiref.local.Localはマルチスレッド、コルーチン両方で使える万能ローカルストレージ

### Q. asgiref.local.Localはなぜコルーチンでも使えるのか？

A.内部でcontextvars.ContextVarを使っているから（このあと詳しく説明します）

## asgiref.local.Localとcontextvars.ContextVarの違い

### contextvars.ContextVarとは

* contextvarsはPythonの標準モジュール
* contextvars.ContextVarは、コンテキスト変数を宣言するためのクラス
* コルーチンごとに固有のコンテキスト変数を使える

### contextvars.ContextVarのサンプルコード

```{revealjs-code-block} python
import threading
from contextvars import ContextVar
import asyncio
import uuid

# threading.localの説明の際に見せた、コルーチンの例とほぼ同じコード。

# コンテキスト変数を宣言
local_storage = ContextVar("local_storage", default=None)

async def test_task(wait):
    start_unique_id = uuid.uuid4().hex
    thread_id = threading.get_ident()
    # 値の設定はset()メソッドで行う（設定できる値は1個のみ）
    local_storage.set(start_unique_id)

    await asyncio.sleep(wait)

    # 値の取得はget()メソッドで行う
    end_unique_id = local_storage.get()
    equal_or_not = "==" if start_unique_id == end_unique_id else "!="
    print(f"{thread_id=} ({start_unique_id=}) {equal_or_not} ({end_unique_id=})")

async def main():
    tasks = (
        test_task(3),
        test_task(2),
        test_task(1),
    )
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-contextvars-contextvar-py>

### contextvars.ContextVarのサンプルコード実行結果

コルーチンごとに固有のローカルストレージが使えることがわかる。

```{revealjs-code-block} shell
thread_id=8308739904 (start_unique_id='011b6db1ddca48b2a353667e9c79f34a') == (end_unique_id='011b6db1ddca48b2a353667e9c79f34a')
thread_id=8308739904 (start_unique_id='dcfc53f6ec9149f99838a6815608c12b') == (end_unique_id='dcfc53f6ec9149f99838a6815608c12b')
thread_id=8308739904 (start_unique_id='42ee7264770745a6b90b9e5e98082a57') == (end_unique_id='42ee7264770745a6b90b9e5e98082a57')
```

<https://gist.github.com/ryu22e/31595bbaf94aa9ec3204651c28e86841#file-contextvars-contextvar-md>

### contextvars.ContextVarの弱点

* contextvars.ContextVarはスレッドセーフではない
* 一応マルチスレッドでも固有のローカルストレージになるが、上記の理由により、実行タイミングによっては予期せぬ挙動になる
* 設定できる値は1個だけ

### つまり

標準モジュールでは、マルチスレッドではthreding.local、コルーチンではcontextvars.ContextVarを使う。

### asgiref.local.Localではどうしているのか

* asgiref.local.Localでは、デフォルトではcontextvars.ContextVarを使って値を設定、取得する
* オプションでthreding.localを使うようにもできる
* 値の取得、設定のコードで排他制御のコードを入れてスレッドセーフになるように工夫している

### `local_storage.unique_id = ...`のような実装を可能にする仕組み

* contextvars.ContextVarは1個の値しか設定できない
* asgiref.local.Localでは辞書型と組み合わせてcontextvars.ContextVarを使っている
    * <https://github.com/django/asgiref/blob/05ae3eee3fae4005ae4cfb0bb22d281725fabade/asgiref/local.py#L12>

## 最後に

### まとめ

* threding.local、contextvars.ContextVarはどちらもローカルストレージとして使えるがそれぞれ弱点がある
* 標準モジュールには万能のローカルストレージはない
* asgiref.local.Localは内部でcontextvars.ContextVarを使い、弱点を補う工夫で万能のローカルストレージを実現している

### ご清聴ありがとうございました

```{figure} thank-you-for-your-attention.*
:alt: AIが考えた「地味だけど便利なasgiref.local.Local」

AIが考えた「地味だけど便利なasgiref.local.Local」
```
