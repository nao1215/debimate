"""答えが 1 つに決まる問題を 100 問作り、problems.json に書く（本記事のために自作した問題集）。

算数 40 問は乱数の seed を固定して生成し、常識 60 問は手で書いた。
使い方: python3 make_problems.py problems.json
"""
import json
import random
import sys

KNOWLEDGE = [
    # (問題, 正解として認める表記)
    ("What is the capital city of Australia?", ["canberra"]),
    ("What is the capital city of Canada?", ["ottawa"]),
    ("What is the capital city of Brazil?", ["brasilia", "brasília"]),
    ("What is the capital city of Turkey?", ["ankara"]),
    ("What is the capital city of Egypt?", ["cairo"]),
    ("What is the capital city of Kenya?", ["nairobi"]),
    ("What is the capital city of Peru?", ["lima"]),
    ("What is the capital city of Norway?", ["oslo"]),
    ("What is the capital city of Vietnam?", ["hanoi", "ha noi"]),
    ("What is the capital city of New Zealand?", ["wellington"]),
    ("What is the capital city of Morocco?", ["rabat"]),
    ("What is the capital city of Argentina?", ["buenos aires"]),
    ("What is the capital city of South Korea?", ["seoul"]),
    ("What is the capital city of Thailand?", ["bangkok"]),
    ("What is the capital city of Nigeria?", ["abuja"]),
    ("What is the chemical symbol for gold?", ["au"]),
    ("What is the chemical symbol for silver?", ["ag"]),
    ("What is the chemical symbol for sodium?", ["na"]),
    ("What is the chemical symbol for potassium?", ["k"]),
    ("What is the chemical symbol for iron?", ["fe"]),
    ("What is the chemical symbol for tungsten?", ["w"]),
    ("What is the chemical symbol for lead?", ["pb"]),
    ("What is the chemical symbol for mercury?", ["hg"]),
    ("Which chemical element has atomic number 1?", ["hydrogen"]),
    ("Which chemical element has atomic number 6?", ["carbon"]),
    ("Which chemical element has atomic number 10?", ["neon"]),
    ("Which planet is the largest in the Solar System?", ["jupiter"]),
    ("Which planet is closest to the Sun?", ["mercury"]),
    ("Which planet is known as the Red Planet?", ["mars"]),
    ("How many legs does a spider have?", ["8", "eight"]),
    ("How many sides does a hexagon have?", ["6", "six"]),
    ("At sea level, what is the boiling point of water in degrees Celsius?", ["100"]),
    ("What is the freezing point of water in degrees Fahrenheit?", ["32"]),
    ("Who wrote the play Romeo and Juliet?", ["shakespeare"]),
    ("Who wrote the novel Pride and Prejudice?", ["austen"]),
    ("Who wrote the novel Nineteen Eighty-Four?", ["orwell"]),
    ("Who painted the Mona Lisa?", ["leonardo", "da vinci"]),
    ("Who painted The Starry Night?", ["van gogh"]),
    ("Who composed the Moonlight Sonata?", ["beethoven"]),
    ("What is the largest ocean on Earth?", ["pacific"]),
    ("What is the longest river in South America?", ["amazon"]),
    ("What is the tallest mountain on Earth above sea level?", ["everest"]),
    ("What is the largest hot desert in the world?", ["sahara"]),
    ("What is the hardest natural mineral?", ["diamond"]),
    ("Which gas do plants absorb from the air for photosynthesis?", ["carbon dioxide", "co2"]),
    ("How many days are in a leap year?", ["366"]),
    ("What is the smallest prime number?", ["2", "two"]),
    ("What is the main language spoken in Brazil?", ["portuguese"]),
    ("What is the currency of Japan?", ["yen"]),
    ("Who developed the theory of general relativity?", ["einstein"]),
    ("Who formulated the three laws of motion published in the Principia?", ["newton"]),
    ("Which organ pumps blood through the human body?", ["heart"]),
    ("How many bones are in the adult human body?", ["206"]),
    ("In which year did humans first land on the Moon?", ["1969"]),
    ("In which year did the Berlin Wall fall?", ["1989"]),
    ("What is the fastest land animal?", ["cheetah"]),
    ("Which programming language was created by Guido van Rossum?", ["python"]),
    ("What is the largest country in the world by area?", ["russia"]),
    ("How many keys does a standard piano have?", ["88"]),
    ("What is the longest bone in the human body?", ["femur"]),
]


def arithmetic(rng):
    items = []
    for _ in range(10):
        a, b = rng.randint(100, 999), rng.randint(100, 999)
        items.append((f"What is {a} + {b}?", [str(a + b)]))
    for _ in range(10):
        a, b = rng.randint(1000, 9999), rng.randint(100, 999)
        items.append((f"What is {a} - {b}?", [str(a - b)]))
    for _ in range(10):
        a, b = rng.randint(11, 99), rng.randint(11, 99)
        items.append((f"What is {a} * {b}?", [str(a * b)]))
    for _ in range(10):
        boxes, per = rng.randint(12, 40), rng.randint(6, 24)
        sold = rng.randint(10, boxes * per - 10)
        items.append((f"A shop has {boxes} boxes with {per} apples in each box. "
                      f"It sells {sold} apples. How many apples are left?",
                      [str(boxes * per - sold)]))
    return items


def main():
    rng = random.Random(20261110)
    problems = []
    for i, (q, a) in enumerate(arithmetic(rng)):
        problems.append({"id": f"math{i:02d}", "kind": "math", "question": q, "answers": a})
    for i, (q, a) in enumerate(KNOWLEDGE):
        problems.append({"id": f"know{i:02d}", "kind": "knowledge", "question": q, "answers": a})
    with open(sys.argv[1], "w") as f:
        json.dump(problems, f, indent=1, ensure_ascii=False)
    print(f"{len(problems)} problems")


if __name__ == "__main__":
    main()
