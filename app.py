from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

OPERATIONS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "×": lambda a, b: a * b,
    "÷": lambda a, b: a / b
}

history = []
BIGGEST = 1e300
MAX_LENGTH = 28
SHOW_STEPS = True


def say(message):
    if SHOW_STEPS:
        print(message)


def normalise(text):
    text = text.replace("*", "×")
    text = text.replace("x", "×")
    text = text.replace("/", "÷")
    return text


def split_into_pieces(text):
    pieces = []
    number = ""

    for character in text:
        if character == " ":
            continue

        if character in "0123456789.":
            number += character

        elif character in OPERATIONS:
            if number == "" or number == "-":
                if character == "-" and number == "":
                    number = "-"
                else:
                    return None
            else:
                pieces.append(number)
                pieces.append(character)
                number = ""

        else:
            return None

    if number == "" or number == "-":
        return None

    pieces.append(number)
    return pieces


def do_math(operator, a, b):
    if operator == "÷" and b == 0:
        say(f"      do_math: {a} ÷ {b} -> division by zero refused")
        return None, "Cannot divide by zero"

    answer = OPERATIONS[operator](a, b)

    say(f"      do_math: {a} {operator} {b} = {answer}")

    if not (-BIGGEST <= answer <= BIGGEST):
        return None, "That number is too big"

    return answer, None


def calculate(expression):
    text = normalise(expression)

    if text.strip() == "":
        return None, "Type a calculation first"

    pieces = split_into_pieces(text)

    say(f"      calculate: pieces = {pieces}")

    if pieces is None:
        return None, "That calculation is not complete"

    numbers = []
    operators = []

    for position in range(len(pieces)):
        if position % 2 == 0:
            try:
                number = float(pieces[position])
            except ValueError:
                return None, "Please enter valid numbers"

            if not (-BIGGEST <= number <= BIGGEST):
                return None, "That number is too big"

            numbers.append(number)
        else:
            operators.append(pieces[position])

    say(f"      calculate: numbers = {numbers}")
    say(f"      calculate: operators = {operators}")

    # First calculate multiplication and division.
    kept_numbers = []
    kept_operators = []
    running = numbers[0]

    for i in range(len(operators)):
        operator = operators[i]
        next_number = numbers[i + 1]

        if operator in ("×", "÷"):
            running, error = do_math(operator, running, next_number)

            if error:
                return None, error
        else:
            kept_numbers.append(running)
            kept_operators.append(operator)
            running = next_number

    kept_numbers.append(running)

    say(f"      calculate: after first pass = {kept_numbers}")

    # Then calculate addition and subtraction.
    answer = kept_numbers[0]

    for i in range(len(kept_operators)):
        answer, error = do_math(
            kept_operators[i],
            answer,
            kept_numbers[i + 1]
        )

        if error:
            return None, error

    say(f"      calculate: final answer = {answer}")

    return answer, None


def show(number):
    if number == int(number):
        return str(int(number))

    return str(round(number, 10))


def pretty(expression):
    pieces = split_into_pieces(normalise(expression))

    if pieces is None:
        return expression

    return " ".join(pieces)


def last_number(text):
    number = ""

    for character in text:
        if character in OPERATIONS:
            number = ""
        else:
            number += character

    return number


def press(text, key, done):
    if key == "C":
        say("      press: clearing the screen")
        return ""

    if key == "⌫":
        say("      press: removing the last character")
        return text[:-1]

    if key in OPERATIONS:
        if text == "":
            if key == "-":
                return "-"
            return text

        last_character = text[-1]

        if last_character in OPERATIONS:
            if len(text) == 1:
                return text

            text = text[:-1]

        return text + key

    if done:
        text = ""

    if key == ".":
        if "." in last_number(text):
            return text

        if last_number(text) == "":
            key = "0."

    if len(text) >= MAX_LENGTH:
        return text

    return text + key


# API route for applications and other programs.
@app.route("/api/calculate")
def api():
    expression = request.args.get("expression", "")

    say("")
    say(f"=== API request: {expression}")

    result, error = calculate(expression)

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "expression": pretty(expression),
        "result": result
    })


# Main calculator webpage.
@app.route("/", methods=["GET", "POST"])
def home():
    expression = ""
    equation = ""
    error = None
    done = False

    if request.method == "POST":
        expression = request.form.get("expression", "")
        key = request.form.get("key", "")
        was_done = request.form.get("done") == "1"

        say("")
        say("=== Calculator button clicked")
        say(f"    Key pressed: {key}")
        say(f"    Current expression: {expression}")

        if key == "=":
            result, error = calculate(expression)

            if error is None:
                equation = pretty(expression) + " ="

                history.insert(
                    0,
                    pretty(expression) + " = " + show(result)
                )

                if len(history) > 10:
                    history.pop()

                expression = show(result)
                done = True

                say(f"    Answer: {expression}")

            else:
                say(f"    Error: {error}")

        else:
            expression = press(expression, key, was_done)

        say(f"    Updated screen: {expression}")

    else:
        say("=== Calculator page opened")

    return render_template(
        "index.html",
        expression=expression,
        equation=equation,
        error=error,
        done=done,
        history=history
    )


if __name__ == "__main__":
    app.run(debug=False)