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

### このトークでお話すること
* asgirefというPythonパッケージの話
* とりわけ、asgiref.local.Localというクラスについての解説

### このトークの対象者
* マルチスレッド、コルーチンなど非同期処理の知識がある人
* トーク中で解説するので、なんとなく知っていればOK

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
* ASGIアプリケーション（非同期処理を行うアプリケーション）を開発しやすくするPythonパッケージ
* Djangoコミュニティが開発している

### asgirefに依存しているツール、フレームワーク
* Daphne
* Django
* Connexion

### 参考資料

以下のドキュメントにasgirefを使ったツール、フレームワークのリストがある。

[asgiref/docs/implementations.rst at main · django/asgiref](https://github.com/django/asgiref/blob/main/docs/implementations.rst)

ただし、バージョンが上がってasgirefに依存しなくなったものも載っている。

## asgiref.local.Localとは何か
TODO 実際に私が開発でasgiref.local.Localを使った経緯を交えて、asgiref.local.Localの使い方について解説します。

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
TODO asgiref.local.Localは標準モジュールthreadingに定義されているlocalとよく似ています。両者の違いについて説明します。

## asgiref.local.Localとcontextvars.ContextVarの違い
TODO asgiref.local.Localの内部では、標準モジュールcontextvarsに定義されているContextVarをラップしています。ContextVarの用途とラップしている理由について説明します。

## 最後に
### まとめ
### ご清聴ありがとうございました
