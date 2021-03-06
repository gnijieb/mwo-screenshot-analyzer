Updated mwo-screenshot-analyzer to V0.3 Contact: gnijieb@gmail.com Github: <https://github.com/gnijieb/mwo-screenshot-analyzer>

DISCLAIMER: Good results will only be achieved when requirements are met.

How do you use it? What does it do?

- put screenshots in input folder
- run script
- get raw data

You basically get the numbers/data from the end-of-round screen (as CSV) to process further (e.g. refer to the google spreadsheet below).

Info/Requirements

- Supported resolutions: 1920x1080, 1920x1200, 2560x1440
- Screenshots should be taken in a non-lossy format (e.g. png using FRAPS), lossy formats like jpg will produce significantly more errors.
- Only Quickplay (Solo or Group) supported

Installation on Windows

- Python Installer

  - Run the installer in resources folder ("python-2.7.11.msi", source: <https://www.python.org/downloads/release/python-2711/>)
  - IMPORTANT: Make sure to tick the option "Add python.exe to Path" in the installer

- tesseract-ocr

  - run the installer in resources folder ("tesseract-ocr-setup-3.05.00dev.exe", source: <https://github.com/UB-Mannheim/tesseract/wiki>
  - IMPORTANT: In installer tick registry settings for PATH

- Get Python modules:

  - Open a Command Prompt (cmd.exe)
  - Change directory to the location of mwo-screenshot-analyzer

    - e.g.: "cd C:\mwo-screenshot-analyzer"

  - Levenshtein:

    - Run: "pip install resources\python_Levenshtein-0.12.0-cp27-none-win32.whl" (source: <http://www.lfd.uci.edu/~gohlke/pythonlibs/#python-levenshtein>)

  - update pip (package manager)

    - run: "python -m pip install -U pip"

  - Python Imaging Library (PIL fork): Pillow

    - run: "pip install Pillow"

  - pytesseract

    - run: "pip install pytesseract"

- create directories in mwo-screenshot-analyzer folder (if not exist): input, output, intermediate, processed

Usage

- You need screenshots of both the player and team stats (end of round) in a specific order (don't mix):

  - first: teamstats, second: playerstats
  - first: playerstats, second: teamstats

- place your screenshots in input directory
- Open a Command Prompt (cmd.exe)
- Change directory to the location of mwo-screenshot-analyzer

  - e.g.: "cd C:\Users\USERNAME\Desktop\mwo-screenshot-analyzer"

- Example with screenshots created with FRAPS (player stats first, team stats second)

  - run: "python analyze.py -p "PLAYERNAME" -t fraps -m3"
  - run: "python analyze.py --help" to see available arguments/usage

- if something is not recognized correctly or as expected, you are asked to open the image in input folder and enter the desired value or select from a given list of best matches
- processed screenshots are moved to the processed folder
- the result is in form of CSV in: output/2016-05-01 20-56-49_data.csv

Optional: External Processing You can create your own external processing module to e.g. submit the data to a database or save it in a specific format. Refer to ext_example.py.

If anyone is interested, feel free to check it out at <https://github.com/gnijieb/mwo-screenshot-analyzer>

OR: Download [Prepackaged ZIP](https://www.dropbox.com/s/3z8r7x93zbu9n03/mwo-screenshot-analyzer_V0.3.zip?dl=0) including Python, Tesseract-OCR installers and prebuilt Python modules (Links to those downloads are also in the README).

Usage is explained in the README file.

EXAMPLE of evaluation: <https://docs.google.com/spreadsheets/d/1L7uE4kvwKsK5Vhcz5K5A7WlRuirLKF70BmLtKdE4454/edit?usp=sharing> (the data on the input tab is the output of the script)

SAMPLE CSV data: <http://pastebin.com/r3rWVTTP>

If you want to contribute/help out or if you encounter any issues, please PM me.
