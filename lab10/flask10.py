#!/usr/bin/python3

from flask import Flask
from flask import request
from flask import abort

app = Flask(__name__)

def calculate(arg1, op, arg2):
    if op == '+':
        return arg1 + arg2
    elif op == '-':
        return arg1 - arg2
    elif op == '*':
        return arg1 * arg2
    else:
        #지원하지 않는 연산자일 경우 처리
        abort(400)


@app.route('/', methods=['POST'])
def postRequest():
    data = request.get_json()
    #필요한 데이터 누락 시 처리
    if not data or 'arg1' not in data or 'op' not in data or 'arg2' not in data:
        abort(400)

    arg1 = data.get('arg1')
    op = data.get('op')
    arg2 = data.get('arg2')

    #피연산자가 숫자가 아닐 경우 처리
    if not isinstance(arg1, int) or not isinstance(arg2, int):
        abort(400)

    result = calculate(arg1, op, arg2)
   
    return {'result': result}
    

@app.route('/<arg1>/<op>/<arg2>')
def getRequest(arg1, op, arg2):
    #피연산자가 숫자가 아닐 경우 처리
    if not arg1.isdigit() or not arg2.isdigit():
        abort(400)

    result = calculate(int(arg1), op, int(arg2))
    
    return {'result': result}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10207)