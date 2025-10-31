# Sokoban Game Solver

This project is a Python implementation of the classic Sokoban game. The game involves pushing boxes onto storage locations within a maze-like environment. The objective is to move all boxes to their respective storage locations without getting stuck in deadlock situations.

## Project Structure

```
sokoban-python
├── src
│   └── sokoban
│       ├── __init__.py
│       ├── point.py
│       ├── sokoban.py
│       ├── deadlock_detector.py
│       ├── state.py
│       ├── search.py
│       ├── map_parser.py
│       └── ui.py
├── formal_inputs
│   └── input_10_10_3_1.txt
├── assets
├── requirements.txt
└── README.md
```

## Instructions to Run the Project

1. **Set Up Python Environment**:
   - Make sure you have Python installed on your machine. You can download it from [python.org](https://www.python.org/).
   - Create a virtual environment (optional but recommended):
     ```
     python -m venv venv
     source venv/bin/activate  # On Windows use `venv\Scripts\activate`
     ```

2. **Install Dependencies**:
   - Navigate to the project directory and install the required packages:
     ```
     pip install -r requirements.txt
     ```

3. **Run the Sokoban Solver**:
   - Navigate to the `src/sokoban` directory and run the `sokoban_solver.py` file:
     ```
     python ui.py
     ```

This will execute the Sokoban game solver using the provided input file.
