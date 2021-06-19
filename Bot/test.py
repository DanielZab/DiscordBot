from subprocess import run
import re
url = "https://www.youtube.com/watch?v=B_HJtVX9fRM"
output = run(f'youtube-dl -o "./test/%(title)s.%(ext)s" --get-duration {url}', capture_output=True).stdout
x = output.decode("utf-8")
print(x)
match = re.match(r"^((?P<h>\d{1,2}(?=\S{4,6})):)?((?P<m>\d{1,2}):)?(?P<s>\d{1,2})$", x)
hours = int(match.group("h") or 0)
minutes = int(match.group("m") or 0)
seconds = int(match.group("s") or 0)
result = hours * 3600 + minutes * 60 + seconds
input(result)
