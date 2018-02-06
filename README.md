# microHMI
A simple and reliable microcontroller oriented Human-Machine Interface made with Kivy 

# Contents

On the master branch you will find the python script, the .kv file that contains the widget structure, the User Guide and a .zip file that contains a standalone executable and its folders.

# Language and libraries

microHMI is being developed in Python 2.7 using Kivy as its graphic toolkit. You can read all about Python [here](https://www.python.org/) and Kivy over [here](https://kivy.org/#home). 

Relational databases are used to store the information. I use [SQLAlchemy](https://www.sqlalchemy.org/), which can be installed via pip.

The communications protocol is Firmata and the Arduino sketch can be found [here](https://www.arduino.cc/en/Reference/Firmata). At server level it is managed by the [PyFirmata library](https://github.com/tino/pyFirmata) which can be installed via pip

# Requirements

For the latest versions of Kivy to work you need to have at least OpenGL ES 2.0 

# OS compatibility

I'm developing microHMI on Windows 8.1 and Ubuntu 16.10. Former versions have been tested in MacOS (specs pending)



