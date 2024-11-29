# 실행 환경

`memo.py`는 Python 3과 Flask를 이용해 구현되었습니다. 현재 코드는 실습 서버 환경에서 작동하는 코드입니다. 하지만 현재 네이버 API 설정을 AWS 배포 버전에 맞춰 놓은 관계로 로그인 API는 작동하지 않습니다. `README.md` 하단에 AWS 배포 버전으로 가는 링크가 있습니다.

# 필요 패키지 설치

`requirements.txt` 파일에는 프로젝트에 필요한 Python 패키지들이 정의되어 있습니다. 다음 명령어

를 이용해 의존성을 설치하십시오. 가상환경(`virtualenv`)을 사용하는 것을 권장합니다.

```bash

$ python3 -m venv .venv
$ source .venv/bin/activate
$ python3 -m pip install -r requirements.txt
```

# 실행 방법

## Flask 서버 실행

- 일반적인 flask 실행 방식대로 실행하면 됩니다.

```bash
$ flask --app memo run --port 포트번호 --host 0.0.0.0
```

- 혹은 다음과 같이 직접 Python 파일을 실행할 수도 있습니다.

```bash
$ python3 memo.py
```

- 후자의 방법으로 실행할 경우 `memo.py` 안에서 port 번호 50207번을 기본값으로 사용하고 있으니 필요 시 수정하세요.

## DB 실행

- DB는 이미 실습 서버에서 아래 명령어로 실행된 상태입니다.

```bash
$ docker run -d \
    --name mysql207 \
    -e MYSQL_ROOT_PASSWORD=your_password \
    -e MYSQL_DATABASE=memo_db \
    -e MYSQL_USER=memo_user \
    -e MYSQL_PASSWORD=your_password \
    -p 50207:3306 \
    mysql:latest
```

- 아래 명령어를 통하여 DB가 실행 중인지 확인하세요.

```bash
$ docker ps filter "name=mysql207"
```

- DB가 실행 중이지 않다면 아래 명령어로 다시 시작하세요.

```bash
$ docker start mysql207
```

# **동작 설명**

### **index.html 읽어 오기**

`memo.py` 를 실행하고 브라우저에서 `http://localhost:50207` 처럼 접근할 경우 `index.html` 을 읽어오게 됩니다.

이는 `Flask` 의 `template` 기능을 사용하고 있으며, 사용되고 있는 `index.html` 의 template file 은 `templates/index.html` 에 위치하고 있습니다.

이 template 은 현재 `name` 이라는 변수만을 외부 변수 값으로 입력 받습니다. 해당 변수는 유저가 현재 로그인 중인지를 알려주는 용도로 사용되며 `index.html` 은 그 값의 유무에 따라 다른 내용을 보여줍니다.

## **index.html 이 호출하는 REST API 들**

```json
{"text": "메모내용"}

```

`index.html` 은 `memo.py` 에 다음 API 들을 호출합니다.

- `GET /login` : authorization code 를 얻어오는 URL 로 redirect 시켜줄 것을 요청합니다. (아래 [네이버 로그인 API 호출](https://github.com/mjubackend/memo_server?tab=readme-ov-file#%EB%84%A4%EC%9D%B4%EB%B2%84-%EB%A1%9C%EA%B7%B8%EC%9D%B8-API-%ED%98%B8%EC%B6%9C) 설명 참고)
- `GET /memo` : 현재 로그인한 유저가 작성한 메모 목록을 JSON 으로 얻어옵니다. 결과 JSON 은 다음과 같은 형태가 되어야 합니다.
    
    ```
    {"memos": ["메모내용1", "메모내용2", ...]}
    ```
    
- `POST /memo` : 새 메모를 추가합니다. HTTP 요청은 다음과 같은 JSON 을 전송해야 됩니다.
    
    ```
    {"text": "메모내용"}
    ```
    
    새 메모가 생성된 경우 memo.py 는 `200 OK` 를 반환합니다.
    

## 네이버 로그인 API 호출

수업 시간에 설명한대로 authorization code 를 얻어오는 동작은 클라이언트에서부터 시작하게 됩니다.

그런데 코드를 보면 `index.html` 에서 해당 API 동작을 바로 시작하는 것이 아니라 `GET /login` 을 통해서 서버에게 해당 REST API 로 redirect 시켜달라고 하는 방식으로 브라우저가 API 를 호출합니다. 이는 Chrome 계열의 브라우저의 `CORS` 문제 때문에 그렇습니다.

비록 서버가 redirect 해주는 방식을 사용하고는 있지만, 클라이언트인 브라우저가 그 API 를 직접 호출한다는 점은 동일합니다.

## **로그인 혹은 가입 처리**

네이버 OAuth 과정을 마무리 한 뒤에 네이버의 profile API 를 통해 얻은 유저의 고유 식별 번호를 갖는 유저가 DB 에 없는 경우 새 유저로 취급하고 DB 에 해당 유저의 이름을 포함하는 레코드를 생성합니다.

만일 같은 네이버 고유 식별 번호의 유저가 있다면 그냥 로그인 된 것으로 간주합니다.

어떤 경우든 DB 에서 해당 유저의 정보를 얻어낼 수 있도록 `userId` 라는 `HTTP cookie` 를 설정합니다.

## **1) `def home()`**

- 사용자가 로그인한 상태라면, `userId` 쿠키를 이용해 DB에서 사용자 이름을 가져와 메인 페이지에 반영합니다.

## **2) `def onOAuthAuthorizationCodeRedirected()`**

- OAuth 과정을 통해 authorization code로부터 access token을 얻고, 이를 이용해 사용자 정보를 DB에 저장한 후 로그인 쿠키를 설정합니다.

## **3) `def getMemos()`**

- 로그인된 사용자의 ID를 이용해 DB에서 해당 사용자의 메모 목록을 조회하고 이를 반환합니다.

## **4) `def post_new_memo()`**

- 로그인된 사용자가 작성한 새로운 메모를 DB에 저장합니다.

# AWS 배포 버전

- 해당 버전을 통해 실제 구현된 로그인 기능과 메모 기능을 확인할 수 있습니다.
- **URL:** [http://memo-server-loadBalancer-1935471691.ap-northeast-2.elb.amazonaws.com/memo](http://memo-server-loadbalancer-1935471691.ap-northeast-2.elb.amazonaws.com/memo)