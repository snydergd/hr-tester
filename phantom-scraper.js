
// Imports
var system = require('system');
var webpage = require('webpage');
var fs = require('fs');

/*
 * This script receives and responds to queries through stdin.
 */
// Set up
var CookieJarFile = system.args[0].replace(new RegExp("[^/]*$"), "") + "cookiejar.json";
if(fs.isFile(CookieJarFile)) {
    Array.prototype.forEach.call(JSON.parse(fs.read(CookieJarFile)), function(x){
        phantom.addCookie(x);
    });
}
//var CookieJar = fs.open(CookieJarFile, "w");
var errors = {
  loggedOut: "logged-out",
  invalidAction: "invalid-action",
  failedConnection: "failed-connection",
  operationCanceled: "operation-canceled",
  networkError: "network-error"
};
console.error = function () {
  system.stderr.write(Array.prototype.join.call(arguments, ' ') + '\n');
  system.stderr.flush();
};
function getPageObj() {
  var page = webpage.create();

  page.onResourceError = function(resourceError) {
    console.error(resourceError.url + ': ' + resourceError.errorString);
    if (resourceError.url == page.url) system.stdout.write(JSON.stringify({success: false, error: errors.networkError})+"\n\n");
  };
  page.onClosing = function(page) { // cookie jar
    fs.write(CookieJarFile, JSON.stringify(phantom.cookies), 'w');
//      CookieJar.seek(0);
//      CookieJar.write(JSON.stringify(phantom.cookies));
//      CookieJar.flush();
  };
  page.onError = function(msg, trace) {
    console.error(msg);
    trace.forEach(function(item) {
      console.error('  ', item.file, ":", item.line);
    });
  };
  return page;
}
var page;
// Log in
function log_in(data, response) {
  page = getPageObj();
	page.open("https://www.hackerrank.com/login", function(status) {
    setTimeout(function () {
      if (status == 'success') {
        page.onUrlChanged = function(url) {
          page.close();
          response.send({success: true});
        };
        page.evaluate(function(data) {
          $(function () {
            if ($(document).find(".login-button").length) {
              $("input#login").val("snydergd");
              $("input#password").val(data.password);
              $(".login-button").click();
            } else {
              window.location.href="/";
            }
          });
          return;
        }, data);
      } else {
        response.send({success: true, error: errors.failedConnection});
      }
    }, 0);
	});
}
// Attempt to open the page
function getPage(data, response) {
  var page = getPageObj();
  page.open(data.url, function(status) {
    if (status == "success") {
//      page.render("page.png");
      page.onCallback = function (result) {
        page.close();
        if (result.isLoggedIn) {
          result["success"] = true;
          response.send(result);
        } else {
          response.send({success: false, error: errors.loggedOut});
        }
      };
      page.evaluate(function () {
        $(function () {
          var result = {};
          result.isLoggedIn = ($(".nav-admin").find(".nav-signup").length == 0);
          if (result.isLoggedIn) {
            var filename = document.location.pathname.split("/");
            var codes = $(".challenge-text pre");
            var testcases = [];
            for (var i = 0; i < codes.length-1; i+=2) testcases.push({input: codes[i].innerText, output: codes[i+1].innerText});
            result.filename = filename[filename.length-1];
            result.title = $(".hr_tour-challenge-name").text().trim();
            result.testcases = testcases;
            result.default_code = lang_default_text;
          }
          window.callPhantom(result);
        });
      });
    } else {
      page.close();
      response.send({success: false, error: errors.failedConnection});
    }
  });
}
// Main input "loop"
(function(){
  var line, input, data, finished = false, process;
  var response = {
    send: function(data) {
      system.stdout.write(JSON.stringify(data) + "\n\n");
      process();
    }
  };
  process = function() {
    if (!system.stdin.atEnd()) {
      input = "";
      line = system.stdin.readLine();
      while (line.length) {
        input += line;
        line = system.stdin.readLine();
      }
      if (input == "") data = null;
      else data = JSON.parse(input);
      if (data != null) {
        switch (data.action) {
          case "getPage":
            getPage(data, response);
            break;
          case "logIn":
            log_in(data, response);
            break;
          default:
            response.send({success: false, error: errors.invalidAction});
        }
        return;
      }
    }
    setTimeout(phantom.exit, 0);
  }
  process();
})();
