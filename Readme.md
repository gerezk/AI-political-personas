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

# Information about the app

Once the command is executed, the application will launch automatically in your default browser. You can then choose to interact with both the Republican and Democrat personas simultaneously or select a single persona. After the models have finished generating their responses, a fact-checker window will appear on the right to review the prompts. Please note that this verification process may take approximately one minute.

# Further information
- for more information about the model versions and evaluation of the political leaning of the personas see the `README.md` in the folder `persona_construction`