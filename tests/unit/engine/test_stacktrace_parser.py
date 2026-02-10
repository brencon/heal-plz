from heal_plz.engine.stacktrace_parser import StacktraceParser


class TestStacktraceParser:
    def setup_method(self):
        self.parser = StacktraceParser()

    def test_python_stacktrace(self):
        trace = '''Traceback (most recent call last):
  File "app/main.py", line 42, in handle_request
    result = process(data)
  File "app/utils.py", line 15, in process
    return data["key"]
KeyError: 'key'
'''
        result = self.parser.parse(trace)
        assert result.language == "python"
        assert len(result.frames) == 2
        assert result.frames[0].file_path == "app/main.py"
        assert result.frames[0].line_number == 42
        assert result.frames[0].function_name == "handle_request"
        assert result.frames[1].file_path == "app/utils.py"
        assert result.frames[1].line_number == 15
        assert result.error_type == "KeyError"

    def test_javascript_stacktrace(self):
        trace = '''TypeError: Cannot read property 'name' of undefined
    at processUser (src/handlers/user.js:25:10)
    at Router.handle (node_modules/express/lib/router.js:174:12)
'''
        result = self.parser.parse(trace)
        assert result.language == "javascript"
        assert len(result.frames) == 2
        assert result.frames[0].file_path == "src/handlers/user.js"
        assert result.frames[0].line_number == 25
        assert result.error_type == "TypeError"

    def test_go_stacktrace(self):
        trace = '''goroutine 1 [running]:
main.handler()
	/app/main.go:42 +0x1a4
net/http.HandlerFunc.ServeHTTP()
	/usr/local/go/src/net/http/server.go:2084 +0x2f
'''
        result = self.parser.parse(trace)
        assert result.language == "go"
        assert len(result.frames) == 2
        assert result.frames[0].file_path == "/app/main.go"
        assert result.frames[0].line_number == 42

    def test_java_stacktrace(self):
        trace = '''java.lang.NullPointerException: Cannot invoke method on null
    at com.app.Service.process(Service.java:42)
    at com.app.Controller.handle(Controller.java:15)
'''
        result = self.parser.parse(trace)
        assert result.language == "java"
        assert len(result.frames) == 2
        assert result.frames[0].file_path == "Service.java"
        assert result.frames[0].line_number == 42
        assert result.error_type == "java.lang.NullPointerException"

    def test_empty_stacktrace(self):
        result = self.parser.parse("")
        assert result.frames == []
        assert result.language is None

    def test_no_stacktrace(self):
        result = self.parser.parse("just some random text")
        assert result.frames == []
