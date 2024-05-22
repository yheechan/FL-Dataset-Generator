from pathlib import Path


script_path = Path(__file__).resolve()
dir = script_path.parent

failing_tcs_txt = dir / 'failing_tcs.txt'
passing_tcs_txt = dir / 'passing_tcs.txt'


# change from TC123 to TC123.sh
def change_format(file):
    new_tc_list = []
    with open(file, 'r') as f:
        lines = f.readlines()
        for line in lines:
            line = line.strip()
            new_tc_list.append(line + '.sh')
    return new_tc_list

def update_file(file, new_tc_list):
    with open(file, 'w') as f:
        f.write('\n'.join(new_tc_list))


def main():
    failing_tcs = change_format(failing_tcs_txt)
    passing_tcs = change_format(passing_tcs_txt)

    update_file(failing_tcs_txt, failing_tcs)
    update_file(passing_tcs_txt, passing_tcs)

if __name__ == '__main__':
    main()

