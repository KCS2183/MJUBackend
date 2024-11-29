from http import HTTPStatus
import random
import requests
import json
import urllib
import string

from flask import abort, Flask, make_response, render_template, Response, redirect, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)


naver_client_id = 'gENmEeM9jyKBdcUl_KnX'
naver_client_secret = '_7TX0j15by'
naver_redirect_uri = 'http://localhost:30207/auth'
'''
  실습서버에서 사용할 경우 http://mjubackend.duckdns.org:본인포트번호/auth 로 하고,
  AWS 에 배포할 때는 http://본인로드밸런서의DNS주소/auth 로 할 것.
'''

# user_id map 선언
user_id_map = {}

# Flask 설정 및 SQLAlchemy 초기화
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://memo_user:60192183@localhost:50207/memo_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 사용자 모델 정의
class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.String(255), primary_key=True)  # 네이버 유저 고유 ID
    name = db.Column(db.String(255), nullable=False)  # 유저 이름

# 메모 모델 정의
class Memo(db.Model):
    __tablename__ = 'memo'
    id = db.Column(db.Integer, primary_key=True) # 메모 고유 ID
    user_id = db.Column(db.String(255), db.ForeignKey('user.id'), nullable=False) # User의 고유 ID 참조
    content = db.Column(db.String(1000), nullable=False) # 메모 내용

    user = db.relationship('User', backref='memos')


@app.route('/')
def home():
    # HTTP 세션 쿠키를 통해 이전에 로그인 한 적이 있는지를 확인한다.
    # 이 부분이 동작하기 위해서는 OAuth 에서 access token 을 얻어낸 뒤
    # user profile REST api 를 통해 유저 정보를 얻어낸 뒤 'userId' 라는 cookie 를 지정해야 된다.
    # (참고: 아래 onOAuthAuthorizationCodeRedirected() 마지막 부분 response.set_cookie('userId', user_id) 참고)
    userId = request.cookies.get('userId', default=None)
    name = None

    ####################################################
    # TODO: 아래 부분을 채워 넣으시오.
    #       userId 로부터 DB 에서 사용자 이름을 얻어오는 코드를 여기에 작성해야 함
    if userId and userId in user_id_map:
        real_user_id = user_id_map[userId]  # 랜덤 키를 통해 실제 user_id 찾기
        user = User.query.get(real_user_id)
        if user:
            name = user.name
    ####################################################


    # 이제 클라에게 전송해 줄 index.html 을 생성한다.
    # template 로부터 받아와서 name 변수 값만 교체해준다.
    return render_template('index.html', name=name)


# 로그인 버튼을 누른 경우 이 API 를 호출한다.
# 브라우저가 호출할 URL 을 index.html 에 하드코딩하지 않고,
# 아래처럼 서버가 주는 URL 로 redirect 하는 것으로 처리한다.
# 이는 CORS (Cross-origin Resource Sharing) 처리에 도움이 되기도 한다.
#
# 주의! 아래 API 는 잘 동작하기 때문에 손대지 말 것
@app.route('/login')
def onLogin():
    params={
            'response_type': 'code',
            'client_id': naver_client_id,
            'redirect_uri': naver_redirect_uri,
            'state': random.randint(0, 10000)
        }
    urlencoded = urllib.parse.urlencode(params)
    url = f'https://nid.naver.com/oauth2.0/authorize?{urlencoded}'
    return redirect(url)


# 아래는 Authorization code 가 발급된 뒤 Redirect URI 를 통해 호출된다.
@app.route('/auth')
def onOAuthAuthorizationCodeRedirected():
    # TODO: 아래 1 ~ 4 를 채워 넣으시오.

    # 1. redirect uri 를 호출한 request 로부터 authorization code 와 state 정보를 얻어낸다.
    authorization_code = request.args.get('code')
    state = request.args.get('state')
    if not authorization_code:
        return 'Authorization Code가 없습니다.', HTTPStatus.BAD_REQUEST


    # 2. authorization code 로부터 access token 을 얻어내는 네이버 API 를 호출한다.
    token_url = 'https://nid.naver.com/oauth2.0/token'
    params = {
        'grant_type': 'authorization_code',
        'client_id': naver_client_id,
        'client_secret': naver_client_secret,
        'code': authorization_code,
        'state': state
    }
    response = requests.post(token_url, data=params)
    token_data = response.json()
    access_token = token_data.get('access_token')

    if not access_token:
        return 'Access Token을 얻어오지 못했습니다.', HTTPStatus.UNAUTHORIZED

    # 3. 얻어낸 access token 을 이용해서 프로필 정보를 반환하는 API 를 호출하고,
    #    유저의 고유 식별 번호를 얻어낸다.
    headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get('https://openapi.naver.com/v1/nid/me', headers=headers)
    profile_data = profile_response.json()
    user_id = profile_data['response']['id']
    user_name = profile_data['response']['name']

    user_id = profile_data['response']['id']
    user_name = profile_data['response']['name']


    # 4. 얻어낸 user id 와 name 을 DB 에 저장한다.
    # user_id = None
    # user_name = None
    user = User.query.get(user_id)
    if not user:
        user = User(id=user_id, name=user_name)
        db.session.add(user)
        db.session.commit()


    # 5. 첫 페이지로 redirect 하는데 로그인 쿠키를 설정하고 보내준다.
    #    user_id 쿠키는 "dkmoon" 처럼 정말 user id 를 바로 집어 넣는 것이 아니다.
    #    그렇게 바로 user id 를 보낼 경우 정보가 노출되기 때문이다.
    #    대신 user_id cookie map 을 두고, random string -> user_id 형태로 맵핑을 관리한다.
    #      예: user_id_map = {}
    #          key = random string 으로 얻어낸 a1f22bc347ba3 이런 문자열
    #          user_id_map[key] = real_user_id
    #          user_id = key
    random_key = ''.join(random.choices(string.ascii_letters + string.digits, k=64))
    user_id_map[random_key] = user_id
    
    response = redirect('/')
    response.set_cookie('userId', random_key)
    return response


@app.route('/memo', methods=['GET'])
def get_memos():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # TODO: DB 에서 해당 userId 의 메모들을 읽어오도록 아래를 수정한다.
    if userId in user_id_map:
        real_user_id = user_id_map[userId]
        # 해당 사용자의 메모를 DB에서 가져옴
        memos = Memo.query.filter_by(user_id=real_user_id).all()
        result = [{'text': memo.content} for memo in memos]
    else:
        result = []

    # memos라는 키 값으로 메모 목록 보내주기
    return {'memos': result}


@app.route('/memo', methods=['POST'])
def post_new_memo():
    # 로그인이 안되어 있다면 로그인 하도록 첫 페이지로 redirect 해준다.
    userId = request.cookies.get('userId', default=None)
    if not userId:
        return redirect('/')

    # 클라이언트로부터 JSON 을 받았어야 한다.
    if not request.is_json:
        abort(HTTPStatus.BAD_REQUEST)

    # TODO: 클라이언트로부터 받은 JSON 에서 메모 내용을 추출한 후 DB에 userId 의 메모로 추가한다.
    memo_content = request.json.get('text', None)
    if not memo_content:
        abort(HTTPStatus.BAD_REQUEST)

    if userId in user_id_map:
        real_user_id = user_id_map[userId]
        # 새로운 메모를 생성하여 DB에 저장
        new_memo = Memo(user_id=real_user_id, content=memo_content)
        db.session.add(new_memo)
        db.session.commit()

    #
    return '', HTTPStatus.OK


if __name__ == '__main__':
    app.run('0.0.0.0', port=50207, debug=True)
