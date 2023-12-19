import requests
import datetime
import re
import os

inputs = {"origin": "", "waypoints": [], "departure_time": "", "avoid": ""}
questions = [
    "出発地点を入力してください",
    "目的地を入力してください（複数可、スペース区切り）",
    "出発日時を入力してください（yyyy/mm/dd hh:mm または now）",
    "有料・高速道路を経路に含めますか？（Y/N）",
]
# APIキーをセット
try:
    API_KEY = os.environ["MAPS_API_KEY"]
except KeyError as k:
    print(k)

# departure_time入力時の指定フォーマット
T_FORMAT = "%Y/%m/%d %H:%"


def drop_delimiter(txt: str) -> str:
    """入力値から句読点を除去"""
    translate_dict = {"、": " ", ",": " "}
    trans_table = txt.maketrans(translate_dict)
    txt = txt.translate(trans_table)
    return txt


def get_unit_time(str_time: str) -> int:
    """departure_timeの入力値に応じてUNIX時間を出力"""
    if str_time == "now":
        return int(datetime.datetime.now().timestamp())
    return int(datetime.datetime.strptime(str_time, T_FORMAT).timestamp())


def is_valid_input(user_input: str, key: str) -> bool:
    """Check user_input is valid"""
    if user_input.isspace() or len(user_input) == 0:
        print("入力が無効です。再度入力してください。")
        return True

    if key == "departure_time":
        date_pattern = r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}"
        is_match = re.match(date_pattern, user_input)
        if user_input != "now" and is_match is None:
            print("日時が無効です。再度入力してください。")
            return True

        try:
            get_unit_time(user_input)
        except ValueError:
            # フォーマットできない値が含まれる（例：13月32日）
            print("日時が正常値ではありませんでした。再度やり直してください。")
            return True

    elif key == "avoid" and user_input not in ["N", "Y"]:
        print("日時が無効です。再度入力してください。")
        return True


#  入力値を取得
def get_inputs() -> None:
    for i, key in enumerate(inputs):
        user_input = input(questions[i])
        while is_valid_input(user_input, key):
            user_input = input(questions[i])

        if key == "waypoints":
            inputs[key] = drop_delimiter(user_input).split()
        elif key == "departure_time":
            inputs[key] = get_unit_time(user_input)
        else:
            inputs[key] = user_input


def get_root(url: str, root_type: str) -> str:
    """MAP APIから結果を取得
    もしルートが見つからない場合は、強制終了

    Args:
        url (str): root_typeによって異なる
        root_type (str): 'optimize' or 'via'
    Returns:
        distance(str): 経由地を経て origin から destination までの距離
        duration(str): 〃 の所要時間
        routs[waypoint_order](list): waypointsを最適な順に並び替えたもの
    """
    res = requests.get(url)
    result = res.json()

    if result["status"] != "OK":
        print(f"ルートが見つかりませんでした。")
        exit()

    routes = result["routes"][0]
    if root_type == "optimize":
        return routes["waypoint_order"]
    elif root_type == "via":
        legs = routes["legs"][0]
        distance = legs["distance"]["text"]
        duration = legs["duration"]["text"]
        return distance, duration


def get_url(root_type: str, order=None) -> str:
    avoid = "&avoid=tolls|highways" if inputs["avoid"] == "N" else ""
    if root_type == "optimize":
        waypoints = ""
        for waypoint in inputs["waypoints"]:
            waypoints += f"%7C{waypoint}"
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={inputs['origin']}&destination={inputs['origin']}&waypoints=optimize%3Atrue{waypoints}&departure_time={inputs['departure_time']}{avoid}&key={API_KEY}"
        return url
    elif root_type == "via":
        waypoints = ""
        for i, v in enumerate(order):
            if i == 0:
                waypoints += f'%3A{inputs["waypoints"][v]}'
            else:
                waypoints += f'%7Cvia%3A{inputs["waypoints"][v]}'
        url = f"https://maps.googleapis.com/maps/api/directions/json?origin={inputs['origin']}&destination={inputs['origin']}&waypoints=via{waypoints}&departure_time={inputs['departure_time']}{avoid}&key={API_KEY}"
        return url


def main():
    get_inputs()
    url = get_url("optimize")
    waypts_order = get_root(url, "optimize")
    url = get_url("via", waypts_order)
    distance, duration = get_root(url, "via")

    root_order = [inputs["waypoints"][w] for w in waypts_order]

    print(f'{inputs["origin"]}から{inputs["waypoints"]}を経由して戻るルートは以下の通りです。')
    print(f"順番：{root_order}")
    print(f"距離: {distance}")
    print(f"所要時間: {duration}")


if __name__ == "__main__":
    main()
