import os


def get_last_success_time():
    if os.path.exists('.conf'):
        with open('.conf', 'r') as f:
            last_success_time = f.read().strip()
            return last_success_time
    else:
        # 文件不存在，返回Unix纪元时间
        return "0"


def update_last_success_time(current_success_time):
    with open('.conf', 'w') as f:
        f.write(current_success_time)
