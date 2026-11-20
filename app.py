from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# ---------------------------------------------------------------------------
# This calculator is built from the same ingredients as the Project 1 calculator:
#   - a dictionary of operations (OPERATIONS)
#   - one function that returns (result, error)   -> calculate()
#   - a history list
#   - two front doors: a web page for people, a JSON route for programs
# There is NO JavaScript. Every button is a form button, and Python decides what it does.
#
# A few small extras are needed (for loops, len, append, a slice). Each one is explained
# where it is used. Anything marked  "FOR FURTHER RESEARCH"  is left out on purpose.
# ---------------------------------------------------------------------------

# One dictionary holds every operation: adding a new one is ONE line.
OPERATIONS = {
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "×": lambda a, b: a * b,
    "÷": lambda a, b: a / b,
}
history = []                    # the last calculations, newest first
BIGGEST = 1e300                 # anything bigger than this is "too big"
MAX_LENGTH = 28                 # the screen holds at most 28 characters

# Set this to False to switch the explaining messages off.
SHOW_STEPS = True


def say(message):
    """Print a message in the terminal (the black window where you started python app.py).
    The messages let you watch what happens after every click."""
    if SHOW_STEPS:
        try:
            print(message)
        except UnicodeEncodeError:
            # Some Windows terminals cannot print symbols like × ÷ ⌫. Print a plain version instead.
            print(message.encode("ascii", "replace").decode())


# ---------------------------------------------------------------------------
# Step 1: tidy the text. People may type x or * for times and / for divide.
# ---------------------------------------------------------------------------
def normalise(text):
    text = text.replace("*", "×")
    text = text.replace("x", "×")
    text = text.replace("/", "÷")
    return text


# ---------------------------------------------------------------------------
# Step 2: cut the text into pieces.
#   "12+3×-4"  becomes  ["12", "+", "3", "×", "-4"]
# We look at ONE character at a time. Digits and dots are collected into "number".
# When we meet an operator, the number is finished, so we save it and the operator.
#
# (A short way to do this is a "regular expression". It is powerful but hard to read.
#  FOR FURTHER RESEARCH: regular expressions, the re module.)
# ---------------------------------------------------------------------------
def split_into_pieces(text):
    """Returns the list of pieces, or None if the text is not a proper sum."""
    pieces = []
    number = ""                                   # the number we are collecting
    for character in text:
        if character == " ":
            continue                              # ignore spaces: go to the next character

        if character in "0123456789.":
            number = number + character           # keep building the number

        elif character in OPERATIONS:
            if number == "" or number == "-":
                # There is no number yet. Only a minus is allowed here, and it
                # means "the next number is negative", for example -5 or 3×-2.
                if character == "-" and number == "":
                    number = "-"
                else:
                    return None                   # for example "×3" or "3++2"
            else:
                pieces.append(number)             # save the finished number
                pieces.append(character)          # save the operator
                number = ""                       # start a new number

        else:
            return None                           # a letter or a strange symbol

    if number == "" or number == "-":
        return None                               # the sum ends with an operator, like "3+"
    pieces.append(number)                         # save the last number
    return pieces


# ---------------------------------------------------------------------------
# Step 3: do one piece of arithmetic, safely.
# ---------------------------------------------------------------------------
def do_math(operator, a, b):
    """Returns (answer, error)."""
    if operator == "÷" and b == 0:
        say(f"      do_math: {a} ÷ {b} -> refused, cannot divide by zero")
        return None, "Cannot divide by zero"
    answer = OPERATIONS[operator](a, b)           # look the operation up in the dictionary
    say(f"      do_math: {a} {operator} {b} = {answer}")
    if answer > BIGGEST or answer < -BIGGEST:
        return None, "That number is too big"
    return answer, None


# ---------------------------------------------------------------------------
# Step 4: the single source of truth. Returns (result, error). One of them is None.
# ---------------------------------------------------------------------------
def calculate(expression):
    text = normalise(expression)
    if text.strip() == "":
        return None, "Type a calculation first"

    pieces = split_into_pieces(text)
    say(f"      calculate: the text '{text}' was cut into pieces: {pieces}")
    if pieces is None:
        return None, "That calculation is not complete"

    # Pieces at positions 0, 2, 4 ... are numbers. Pieces at positions 1, 3, 5 ... are operators.
    # Turn the numbers from text into real numbers, just like the Project 1 calculator does.
    numbers = []
    operators = []
    for position in range(len(pieces)):
        if position % 2 == 0:                     # an even position: a number
            try:
                number = float(pieces[position])
            except ValueError:
                return None, "Please enter valid numbers"
            if number > BIGGEST or number < -BIGGEST:
                return None, "That number is too big"
            numbers.append(number)
        else:                                     # an odd position: an operator
            operators.append(pieces[position])
    say(f"      calculate: numbers = {numbers}")
    say(f"      calculate: operators = {operators}")

    # -----------------------------------------------------------------------
    # FOR FURTHER RESEARCH: "operator precedence".
    # A real calculator works out × and ÷ BEFORE + and -, so 2+3×4 is 14, not 20.
    # We do it in two passes over the list:
    #   Pass 1 works out every × and ÷ and keeps only the + and - for later.
    #   Pass 2 works out the + and - from left to right.
    # (To make a calculator that simply goes left to right, delete pass 1 and run
    #  pass 2 on the original "numbers" and "operators".)
    # -----------------------------------------------------------------------

    # Pass 1: × and ÷
    kept_numbers = []                             # numbers that are left after pass 1
    kept_operators = []                           # only + and - are left after pass 1
    running = numbers[0]                          # the number we are working on
    for i in range(len(operators)):
        operator = operators[i]
        next_number = numbers[i + 1]
        if operator == "×" or operator == "÷":
            running, error = do_math(operator, running, next_number)
            if error is not None:
                return None, error
        else:                                     # a + or -: put it aside for pass 2
            kept_numbers.append(running)
            kept_operators.append(operator)
            running = next_number
    kept_numbers.append(running)
    say(f"      calculate: after pass 1 (× and ÷ done): numbers = {kept_numbers}, operators = {kept_operators}")

    # Pass 2: + and -, from left to right
    answer = kept_numbers[0]
    for i in range(len(kept_operators)):
        answer, error = do_math(kept_operators[i], answer, kept_numbers[i + 1])
        if error is not None:
            return None, error

    say(f"      calculate: after pass 2 (+ and - done): answer = {answer}")
    return answer, None


# ---------------------------------------------------------------------------
# Small helpers for showing things nicely
# ---------------------------------------------------------------------------
def show(number):
    """5.0 becomes '5'.  0.30000000000000004 becomes '0.3'."""
    if number == int(number):                     # a whole number such as 5.0
        return str(int(number))
    return str(round(number, 10))                 # round to 10 decimal places


def pretty(expression):
    """'3+2×4' becomes '3 + 2 × 4' (spaces between the pieces)."""
    pieces = split_into_pieces(normalise(expression))
    if pieces is None:
        return expression                         # not a proper sum: show it as typed
    text = ""
    for piece in pieces:
        text = text + piece + " "
    return text.strip()                           # strip() removes the extra space at the end


def last_number(text):
    """The number being typed right now. '12+3.5' gives '3.5'."""
    number = ""
    for character in text:
        if character in OPERATIONS:
            number = ""                           # an operator ends the number
        else:
            number = number + character
    return number


# ---------------------------------------------------------------------------
# Step 5: what does each keypad button do? This is the "brain" of the keypad.
# It takes the text on the screen and the key that was pressed,
# and gives back the new text for the screen.
# ---------------------------------------------------------------------------
def press(text, key, done):
    """done is True right after an answer was shown."""
    if key == "C":
        say("      press: C was pressed, so the screen is cleared")
        return ""                                 # clear everything

    if key == "⌫":
        say("      press: ⌫ was pressed, so the last character is removed")
        # FOR FURTHER RESEARCH: slicing. text[:-1] means "everything except the last character".
        return text[:-1]

    if key in OPERATIONS:                         # + - × ÷
        say(f"      press: '{key}' is an operator")
        if text == "":
            if key == "-":
                say("      press: the screen is empty, a minus is allowed at the start")
                return "-"                        # a sum may start with a minus sign
            say("      press: the screen is empty, a sum cannot start with this operator, so nothing changes")
            return text                           # but not with + × ÷
        last_character = text[len(text) - 1]
        if last_character in OPERATIONS:          # an operator is already at the end
            if len(text) == 1:
                say("      press: the screen is only a minus sign, so nothing changes")
                return text                       # the text is only "-", leave it
            say(f"      press: the text already ends with '{last_character}', so the new operator replaces it")
            text = text[:-1]                      # remove it, so the new operator replaces it
        return text + key

    # Anything else is a digit or the dot.
    say(f"      press: '{key}' is a digit or the dot")
    if done:
        say("      press: an answer was just shown, so typing a digit starts a NEW sum")
        text = ""                                 # typing a digit after an answer starts a new sum
    if key == ".":
        if "." in last_number(text):
            say("      press: this number already has a dot, so nothing changes")
            return text                           # one dot per number is enough
        if last_number(text) == "":
            say("      press: a dot on its own becomes 0.")
            key = "0."                            # a dot on its own becomes 0.
    if len(text) >= MAX_LENGTH:
        say("      press: the screen is full, so nothing changes")
        return text                               # the screen is full
    return text + key


# Front door 1: for programs  ->  JSON
@app.route("/api/calculate")
def api():
    expression = request.args.get("expression")
    if expression is None:
        expression = ""
    say("")
    say(f"=== The JSON door was used with expression '{expression}'")
    result, error = calculate(expression)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"expression": pretty(expression), "result": result})


# Front door 2: for people  ->  HTML page with a keypad
# Every key press is a POST. The page sends back the text on the screen (hidden in the form),
# the key that was pressed, and whether an answer was just shown.
@app.route("/", methods=["GET", "POST"])
def home():
    expression = ""             # the text on the screen
    equation = ""               # the small line above the screen
    error = None
    done = False                # True right after "=", so the next digit starts a new sum
    if request.method == "POST":
        expression = request.form["expression"]
        key = request.form["key"]
        was_done = request.form["done"] == "1"
        say("")
        say("=== A button was clicked: the browser sent a POST to Python")
        say(f"    key pressed          : '{key}'")
        say(f"    text on the screen   : '{expression}'")
        say(f"    answer just shown?   : {was_done}")

        if key == "=":
            say("    -> '=' means: work out the answer (calculate)")
            result, error = calculate(expression)
            if error is None:
                equation = pretty(expression) + " ="
                history.insert(0, pretty(expression) + " = " + show(result))
                if len(history) > 10:
                    history.pop()                     # remove the oldest one
                expression = show(result)
                done = True
                say(f"    -> answer is {expression}; it is added to the history (now {len(history)} items)")
            else:
                say(f"    -> refused with the message: {error}")
        else:
            say("    -> any other key means: change the text on the screen (press)")
            expression = press(expression, key, was_done)

        say(f"    text on the screen after: '{expression}'")
        say("    -> the page is sent back to the browser")
    else:
        say("")
        say("=== The page was opened (GET): showing an empty calculator")

    return render_template("index.html", expression=expression, equation=equation,
                           error=error, done=done, history=history)


if __name__ == "__main__":
    app.run(debug=False)
