#!/bin/env python3

import argparse
from os.path import basename, dirname, exists, expanduser, isdir, abspath
from os import getcwd, system, mkdir, chdir, mknod, remove as rm, write, close, waitpid, fork, dup2, O_RDONLY, O_WRONLY, open as os_open, execv, pipe, setpgrp, wait, close, kill, read, set_inheritable, isatty, rename
import sys, subprocess, re, json, argcomplete, pyperclip, tempfile, time
from io import StringIO
from glob import iglob, glob
import collections
import signal
import resource, shlex, getpass

pyperclip.set_clipboard("xsel") # For some reason my setup needs this

## Functions
def editor_prompt(prompt_text, suffix=".txt"):
  fd, name = tempfile.mkstemp(suffix=suffix)
  write(fd, (prompt_text + "\n").encode("utf-8"))
  close(fd)
  system(config["editor"] + " " + name);
  with open(name, "r") as f:
    for i in range(prompt_text.count("\n")+1):
      f.readline()
    input = f.read()
  rm(name)
  return input
def dict_update(d, u):
  for k, v in u.items():
    if isinstance(v, collections.Mapping):
      r = dict_update(d.get(k, {}), v)
      d[k] = r
    else:
      d[k] = u[k]
  return d
# Get challenge information from website using PhantomJS
def fetchProblemInfo(url):
  p = subprocess.Popen(["phantomjs", dirname(__file__) + "/phantom-scraper.js"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
  def resultFromPhantom(query):
    p.stdin.write((json.dumps(query)+'\n\n').encode("utf-8"))
    p.stdin.flush()
    buff = StringIO()
    line = p.stdout.readline()
    while len(line.strip()) > 0:
      buff.write(line.decode("utf-8"))
      line = p.stdout.readline()
    return json.loads(buff.getvalue())
  result = resultFromPhantom({'action': 'getPage', 'url': url})
  if (not result["success"] and result["error"] == "logged-out"):
    attempts = 0
    while (not result["success"] and attempts < 3):
      password = getpass.getpass("Password for Hackerrank: ")
      result = resultFromPhantom({'action': 'logIn', 'password': password})
      attempts += 1
    if (not result["success"]):
      print("After 3 attempts, just proceeding without info from online.")
    else:
      result = resultFromPhantom({'action': 'getPage', 'url': url})
      if not result["success"]:
        print("Despite successful log-in, couldn't get content from Hackerrank.  Proceeding without it.")
  return result

### Run async subprocess with time limit, keeping track of execution time
STDOUT_FILENO = 1
timed_out = False
timing_pid = 0
def handle_timeout(signum, frame):
  global timed_out, timing_pid
  timed_out = True
  kill(timing_pid, signal.SIGINT)
signal.signal(signal.SIGVTALRM, handle_timeout)
STDIN_FILENO = 0
STDERR_FILENO = 2
def time_subprocess(command, output_limit, time_limit, input_file):
  global timed_out, timing_pid
  errfile,errfilename = tempfile.mkstemp()
  piper, pipew = pipe()
  set_inheritable(pipew, True)
  set_inheritable(piper, False)
  timed_out = False
  timing_pid = fork()
  t1 = resource.getrusage(resource.RUSAGE_CHILDREN)
  t1 = t1.ru_utime + t1.ru_stime
  if (timing_pid == 0):
    dup2(pipew, STDOUT_FILENO)
    dup2(os_open(input_file, O_RDONLY), STDIN_FILENO)
    if config["error_file"] != None:
      dup2(os_open(config["error_file"], O_WRONLY), STDERR_FILENO)
    else:
      dup2(errfile, STDERR_FILENO)
    close(pipew)
#    usage = resource.getrusage(resource.RUSAGE_SELF)
#    write(STDOUT_FILENO, (str(usage.ru_utime+usage.ru_stime)+"\n").encode("utf-8"))
    signal.setitimer(signal.ITIMER_VIRTUAL, time_limit)
    execv("/bin/sh", ["sh", "-c", command])
    print("Couldn't run executable")
  elif timing_pid == -1:
    print("Could not create child process!")
  else:
    dup2(piper, STDIN_FILENO)
#    t1 += float(sys.stdin.readline())
#    signal.setitimer(signal.ITIMER_VIRTUAL, time_limit)
    pid, rv = wait()
    if rv == 26:
      timed_out = True
    close(errfile)
    with open(errfilename, "r") as f:
      errstring = f.read()
    rm(errfilename)
    t2 = resource.getrusage(resource.RUSAGE_CHILDREN)
    t2 = t2.ru_utime + t2.ru_stime
    close(piper)
    close(pipew)
    result = StringIO()
    i = 0
    line = sys.stdin.readline()
    while (i < output_limit and line != ""):
      result.write(line)
      line = sys.stdin.readline()
      i += 1
    return (t2-t1, result.getvalue(), rv, errstring)
class Color:
  green  = "\x1b[1;32m"
  red    = "\x1b[1;31m"
  yellow = "\x1b[1;33m"
  reset  = "\x1b[1;0m"
  def init():
    if (not isatty(STDOUT_FILENO)):
      Color.green = Color.red = Color.yellow = Color.reset = ""
Color.init()

## Config
LOCAL_CONFIG=".hackerrank.json"
CONFIG_DIR=expanduser("~/.hackerrank/")
def configFile(name):
  if (name[0] == "/"):
    return name
  else:
    return CONFIG_DIR + name
CONFIG_FILE = configFile("settings.json")
config = {
  "challenge_directory": "./",
  "editor": "nano",
  "default_mode": "cpp",
  "max_output_lines": 40,
  "error_file": None,
  "modes": {
    "cpp": { # default mode
      "max_exec_time": 2,
      "template_file": "template.cpp",
      "source_extension": ".cpp",
      "exe_extension": "",
      "run_command": "./{exe}",
      "compile_command": "g++ {source} -o {exe}"
    },
    "cs": {
      "template_file": "template.cs",
      "source_extension": ".cs",
      "compile_command": "dmcs {source} -out:{exe}"
    }
  }
}
if (not exists(CONFIG_DIR)):
  mkdir(CONFIG_DIR)
if exists(CONFIG_FILE):
  with open(CONFIG_FILE, "r") as f:
    dict_update(config, json.load(f))
else:
  with open(CONFIG_FILE, "w") as f:
    json.dump(config, f, indent=2)
if exists(LOCAL_CONFIG):
  with open(LOCAL_CONFIG, "r") as f:
    dict_update(config, json.load(f))
config["challenge_directory"] = expanduser(config["challenge_directory"])

## Arg Parser
def get_arguments():
  parser = argparse.ArgumentParser(description="Hackerrank competition tools")
  parser.add_argument("-s", dest="extra_settings", help="Configuration key overrides, e.g. modes.cpp.max_exec_time=5")
  parser.add_argument("-m", dest="mode", help="Mode to use (e.g. cpp)", default=config["default_mode"], choices=config["modes"].keys())
  parser.add_argument("-S", dest="source", help="Source file to use in test")
  subparsers = parser.add_subparsers(help="Command to run", dest="command")

  show_parser = subparsers.add_parser("show", help="Show information about hackerrank stuff")
  show_parser.add_argument("key", help="What piece of information to show", choices=["dir"])

  init_parser = subparsers.add_parser("init", help="Initialize a directory for a challenge")
  init_parser.add_argument("-t", action="store_true", dest="custom_testcases", help="Prompt for custom testcases", required=False)
  init_parser.add_argument("slug", help="Slug or URL of challenge [page].", nargs="?", default=None)

  test_parser = subparsers.add_parser("test", help="Test code in current challenge directory")
  test_parser.add_argument("-n", dest="number", help="Which test case to run") #, choices=list(map(lambda x: re.match(r".*input([^/]*)\.txt$", x).group(1), glob("**/input*.txt", recursive=True))))

  edit_parser = subparsers.add_parser("edit", help="Edit source")
  edit_parser.add_argument("target", help="What to edit", choices=["hackerrank.py", "challenge", "config", "localconfig", "template"], default="challenge", nargs="?")

  stash_parser = subparsers.add_parser("stash", help="Stash source file and start over")
  stash_parser.add_argument("-v", "--version", help="Use the specified version, instead of starting from scratch", type=int, required=False, default=None)
  stash_parser.add_argument("-s", "--show", help="Show available versions", action="store_true")
  stash_parser.add_argument("-r", "--remove", help="When restoring a version, remove current version", action="store_true")

  paste_parser = subparsers.add_parser("paste", help="Put content from clipboard into a file")
  paste_parser.add_argument("destination", help="Where to put clipboard contents", choices=["source", "input", "output"], default="source", nargs="?")

  argcomplete.autocomplete(parser)
  return parser.parse_args()

## Main
if __name__ == "__main__":
  args = get_arguments()

  ### Config based on arguments
  if args.extra_settings != None:
    if type(args.extra_settings) != list:
      args.extra_settings = [args.extra_settings]
    for item in args.extra_settings:
      if (item[-1] == "="):
        val = None
        key = item[:-1]
      else:
        key, val = item.split("=")
        if val.isdigit():
          val = int(val)
      key = key.split(".")
      c = config
      for child in key[:-1]:
        c = c[child]
      c[key[-1]] = val
  mode_config = config["modes"]["cpp"] # start with default mode
  dict_update(mode_config, config["modes"][args.mode])
  url = None
  if (args.command == "init"):
    if args.slug == None:
      if "challenge_url" in config:
        url = config["challenge_url"]
        args.slug = re.sub(r".*challenges/([^/?]+).*", "\\1", url)
      elif abspath(config["challenge_directory"]) == abspath(getcwd()+"/../"):
        args.slug = basename(getcwd())
      else:
        print("I don't know what challenge you're talking about because you're not in a challenge directory and you didn't specify one.")
        exit(1)
    if "/" in args.slug:
      url = args.slug
      args.slug = re.sub(r".*challenges/([^/?]+).*", "\\1", args.slug)
  if args.source != None:
    source_file = args.source
    newmode = None
    for mode in config["modes"]:
      if (source_file[-len(config["modes"][mode]["source_extension"]):] == config["modes"][mode]["source_extension"]):
        newmode = mode
    if newmode == None:
      print("Using default mode: " + args.mode + " since we couldn't identify one from the extension")
    else:
      args.mode = newmode
  elif args.command == "init":
    source_file = args.slug + mode_config["source_extension"]
  else:
    source_file = basename(getcwd()) + mode_config["source_extension"]
  mode_config["template_file"] = configFile(mode_config["template_file"])
  if not exists(mode_config["template_file"]):
    mknod(mode_config["template_file"])

  ### Show
  if (args.command == "show"):
    if (args.key == "dir"):
      print(config["challenge_directory"])
  ### Paste
  elif (args.command == "paste"):
    if (args.destination == "source"):
      with open(source_file, "w") as f:
        f.write(pyperclip.paste())
        print("Pasted")
  ### Edit
  elif (args.command == "edit"):
    if (args.target == "hackerrank.py"):
      system(config["editor"] + " " + __file__)
    elif args.target == "config":
      system(config["editor"] + " " + configFile("settings.json"))
    elif args.target == "localconfig":
      system(config["editor"] + " " + LOCAL_CONFIG)
    elif args.target == "template":
      system(config["editor"] + " " + mode_config["template_file"])
    else:
      system(config["editor"] + " " + source_file)
  ### Test
  elif (args.command == "test"):
    if not exists(source_file):
      print("Could not find {file}, aborting".format(file=source_file))
    else:
      if mode_config["compile_command"] == None or (system(mode_config["compile_command"].format(source=source_file, exe=re.sub(r"\.[^.]+$", "", source_file)+mode_config["exe_extension"])) == 0):
        print("Testing executable {0}".format(re.sub(r"\.[^.]+$", "", source_file)+mode_config["exe_extension"]))
        good = 0
        total = 0
        other = 0
        tod = 0
        if args.number != None:
          if (exists("input{0}.txt".format(args.number))):
            files = ["input{0}.txt".format(args.number)]
          else:
            files = ["input/input{0}.txt".format(args.number)]
        else:
          files = sorted(glob("**/input*.txt", recursive=True))
        for file in files:
          if total > 0:
            print("---------------------")
          total += 1
          tc_spec = re.match("input(.*)\.txt$", file).group(1)
          outfn = file.replace("input", "output")
          exe_time, result, rv, errstring = time_subprocess(mode_config["run_command"].format(exe=re.sub(r"\.[^.]+$", "", source_file)+mode_config["exe_extension"]), config["max_output_lines"], mode_config["max_exec_time"], file)
          sys.stdout.write("TC %s (%.2fs): " % (tc_spec, exe_time))
          if timed_out:
            tod += 1
            print("{yellow}TIMED OUT{reset}\n{result}".format(yellow=Color.yellow, reset=Color.reset, result=result))
          elif rv != 0:
            print("{yellow}RUNTIME ERROR ({code})\n{err}{reset}".format(yellow=Color.yellow, reset=Color.reset, code=rv, err=errstring))
          else:
            if exists(outfn):
              with open(outfn, 'r') as f:
                expected_result = f.read()
              if result.strip() == expected_result.strip():
                good += 1
                print("{green}PASS{reset}".format(green=Color.green, reset=Color.reset))
              else:
                print("{red}FAIL{reset}\nExpected Output:\n'{expected}'\nReceived Output:\n'{received}'".format(expected=expected_result.strip().replace("\n", "'\n'"), received=result.strip().replace("\n", "'\n'"), red=Color.red, reset=Color.reset))
            else:
              other += 1
              print("{yellow}No expected output, dumping output...{reset}".format(yellow=Color.yellow, reset=Color.reset))
              print(result)
        print("{0}/{1} testcases passed, {2} timed out, {3} with unknown result, {4} failed.".format(good, total, tod, other, total-good-tod-other))
      else:
        print("Compiling failed for %s" % source_file)
  ### Stash
  elif args.command == "stash":
    if args.version != None:
      otherf = re.sub(r"(\.[^.]+)$", "{0}\\1".format(args.version), source_file)
      if (args.remove):
        rename(otherf, source_file)
      else:
        rename(otherf, "." + otherf)
        rename(source_file, otherf)
        rename("." + otherf, source_file)
    if args.show:
      print(list(filter(lambda x: re.match(re.sub("(\.[^.]+)$", "\d\\1", source_file), x), iglob(re.sub("(\.[^.]+)$", "*\\1", source_file)))))
    if args.version == None and not args.show:
      i = 0
      while exists(re.sub(r"(\.[^.]+)$", "{0}\\1".format(i), source_file)):
        i += 1
      old_file = re.sub(r"(\.[^.]+)$", "{0}\\1".format(i), source_file)
      rename(source_file, old_file)
      template = ""
      if "challenge_url" in config:
        result = fetchProblemInfo(config["challenge_url"])
        if (result["success"] and args.mode in result["default_code"]):
          template = result["default_code"][args.mode]
      if template == "":
        with open(configFile(config["template_file"]), "r") as f:
          template = f.read()
      with open(source_file, "w") as f:
        f.write(template)
  ### Init
  elif args.command == "init":
    # Get ready to make changes
    chdir(config["challenge_directory"])

    # Directory creation/entry
    if not exists(args.slug):
      mkdir(args.slug)
    elif isdir(args.slug):
      answer = "d"
      while (answer != "y" and answer != "n" and answer != ""):
        sys.stdout.write("{0} appears to already exist.  Would you like to initialize into that directory? (Y/n) ".format(args.slug))
        answer = input()
      if (answer.lower() == "n"):
        print("Not using this directory")
        sys.exit(1)
    else:
      print("{0} exists but is not a directory!  Please delete or move it and try again.".format(args.slug))
      sys.exit(1)
    chdir(args.slug)

    # Initial source file setup
    i = 0 # number of currently available testcase number (based on what files exist)
    if (url != None):
      result = fetchProblemInfo(url)
      if not result["success"]:
        url = None
    if url == None:
      print("Using template file %s" % mode_config["template_file"])
      with open(configFile(mode_config["template_file"]), 'r') as f, open(source_file, "w") as f2:
        f2.write(f.read())
    else:
      print("Got Hackerrank details for contest " + result["title"])
      for j in range(len(result["testcases"])):
        with open("inputHR{0}.txt".format(j), "w") as f:
          f.write(result["testcases"][j]["input"])
        with open("outputHR{0}.txt".format(j), "w") as f:
          f.write(result["testcases"][j]["output"])
      with open(source_file, "w") as f:
        if (args.mode in result["default_code"]):
          f.write(result["default_code"][args.mode])
        else:
          with open(configFile(mode_config["template_file"]), 'r') as f2:
            f.write(f2.read())

    # Local config file creation
    localConfig = {}
    if (url != None):
      localConfig["challenge_url"] = url
    if exists(LOCAL_CONFIG):
      with open(LOCAL_CONFIG, "r") as f:
        localConfig.update(json.load(f))
    localConfig["default_mode"] = args.mode
    with open(LOCAL_CONFIG, "w") as f:
      json.dump(localConfig, f, indent=2)

    # Read custom test cases
    while (args.custom_testcases):
      while exists("input{0}.txt".format(i)):
        i += 1
      # Test Case Input
      tc = editor_prompt("Enter testcase {0} INPUT below, or exit.  Remember to save.".format(i))
      if (len(tc) == 0):
        break
      with open("input{0}.txt".format(i), "w") as f:
        f.write(tc)

      # Test Case Output
      tc = editor_prompt("Enter testcase {0} OUTPUT below, or exit.  Remember to save.".format(i))
      if (len(tc) == 0):
        break
      with open("output{0}.txt".format(i), "w") as f:
        f.write(tc)

      i += 1
    # Finished
    print("All done!  Created directory %s." % args.slug)
