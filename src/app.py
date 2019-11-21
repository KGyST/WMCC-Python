from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/test-app", methods=['GET'])
def test_endpoint():
    return jsonify({"test": "it's working!"})

@app.route("/", methods=['POST'])
def archicad_engine():
    some_json = request.get_json()
    return jsonify({"result": some_json})

if __name__ == '__main__':
    app.run(debug=True)
