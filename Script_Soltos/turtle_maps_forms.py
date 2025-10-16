# -*- coding: utf-8 -*-

__author__ = 'Edson Luiz'

import turtle
import random
import math

# Setup screen
screen = turtle.Screen()
screen.bgcolor("black")
screen.title("Turtle Maps - by Edson Luiz")

# Setup turtle
t = turtle.Turtle()
t.speed(0)
t.hideturtle()

# Color palette
colors = ["cyan", "magenta", "yellow", "white", "lime", "orange", "violet", "red"]

# Shape functions
def draw_square(size):
    for _ in range(4):
        t.forward(size)
        t.right(90)

def draw_triangle(size):
    for _ in range(3):
        t.forward(size)
        t.right(120)

def draw_circle(size):
    t.circle(size / 2)

def draw_star(size):
    for _ in range(5):
        t.forward(size)
        t.right(144)

# Random art generator
shapes = [draw_square, draw_triangle, draw_circle, draw_star]

for _ in range(80):
    t.penup()
    t.goto(random.randint(-300, 300), random.randint(-250, 250))
    t.pendown()
    t.color(random.choice(colors))
    size = random.randint(20, 80)
    random.choice(shapes)(size)
    t.right(random.randint(0, 360))

turtle.done()
