# Setup

To setup the project, you can use one of the two scripts below (depending on your operating system). You must have Python 3.12 installed.

**Windows**

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
./setup.ps1
.\.venv\Scripts\Activate.ps1
```

**Linux**

```
chmod +x ./setup.sh
./setup.sh
source .venv/bin/activate
```

These scripts will set up a Python environment and install all necessary dependencies. Furthermore, all of the necessary models will be pulled and created.

The app can then be run using the following command in the project directory:

```
chainlit run frontend.py -w
```