# Passbolt auto-renewer

This tool allows to quickly update a given set of passwords from passbolt. It will help you doing so by automatically :

* Select a set of passwords based on multiple criterias
* Create a new password
* Update the password where it is defined (API, Apache2 HTTP Basic, XWiki, ...)
* Update the password in Passbolt

## Installation and configuration

### Prerequisites

This tool relies on 3 tools :
* Python3
* [Virtualenv](https://virtualenv.pypa.io/en/stable/) to locally install Python packages needed for the tool
* GnuPG to manage PGP keys that the tool deals with when communicating with Passbolt

Make sure that you have those three dependencies satisfied before going further.

### Installation

Clone the project repository :
```
git clone git@git.xwikisas.com:passbolt-tools/renewer.git
cd renewer
```

Set-up the virtual environment :
```
virtualenv -p $(which python3) venv
source venv/bin/activate
```

Install the project packages :
```
pip install -r requirements.txt
```

Once this is done, you're good to go. For later, when you need to use the tool in a new shell, simply do :
```
source venv/bin/activate
```
... before running the script itself : this allows the tool to access its python-specific packages (stored in `venv/`)

### First configuration

