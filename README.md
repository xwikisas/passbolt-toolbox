# Passbolt auto-renewer

This tool allows to quickly update a given set of passwords from passbolt. It will help you doing so by automatically :

* Select a set of passwords based on multiple criterias
* Create a new password
* Update the password where it is defined (API, Apache2 HTTP Basic, XWiki, ...)
* Update the password in Passbolt

## Overview

On its first start, the tool will create a directory `~/.password-renewer` storing all of its configuration, this includes :
* The tool configuration
* The GnuPG keyring used by the tool

In order to properly communicate with Passbolt, the tool needs to know the following information :
* The public key of the Passbolt server (this key should be trusted *ultimately* by GnuPG)
* The private key of the user that you will use for authentication on the server (this key should also be *ultimately* trusted)
* The address of the server

Those information are stored in `~/.passbolt-renewer/config.json`. You can refer to this file in case something goes wrong. Here is an example a file :

```
{
    "server": {
        "fingerprint": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
        "uri": "https://passbolt.mycompany.com",
        "verifyCert": false
    },
    "user": {
        "fingerprint": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    }
}
```

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

In order to understand the following steps, please refer to the *Overview* section.

#### Server configuration

We'll first start by configuring the Passbolt server. As getting the public key of the server is usually teadious without relying on the REST API of the server, this step is partially automated.

You can run `passbolt-renewer setup` to start the setup of the server. If a server was previously set up, the tool will ask before overwriting the server configuration.

> In case your server is configured with HTTPS but does not provide its [certificate chain](https://support.dnsimple.com/articles/what-is-ssl-certificate-chain/), you will need to answer YES to the question `Trust the server certficate without verification ?`.

This option will simply get the fingerprint of the server and its public key for you and import it in the tool keyring.

#### User configuration

This part is not automated yet :/ however, it's supposed to be more simple than the server part. Before continuing, make sure that you have a local copy of your Passbolt private key.

First, import your key in the application keyring :
```
gpg --homedir ~/.passbolt-renewer/gnupg --import <your_file>
```

You can now see your imported key with `gpg --homedir ~/.passbolt-renewer/gnupg --list-secret-keys`, here is an example :
```
~/.passbolt-renewer/gnupg/pubring.gpg
------------------------------------------------
sec   rsa2048 2019-05-28 [SC]
      XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
uid           [ unknown] Your Name <your email at xwiki.com>
ssb   rsa2048 2019-05-28 [E]
```

You will need to copy-paste your key fingerprint in the `user.fingerprint` field of `~/passbolt-renewer/config.json`.

The last step is to make sure that your key is fully trusted by GnuPG. Without that, the authentication to the Passbolt will not work. Here is how to do it :

```
you@yourMachine:~ % gpg --homedir ~/.passbolt-renewer/gnupg --edit-key XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
gpg (GnuPG) 2.2.12; Copyright (C) 2018 Free Software Foundation, Inc.
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.

Secret key is available.

sec  rsa2048/XXXXXXXXXXXXXXXX
     created: 2019-05-28  expires: never       usage: SC  
     trust: unknown       validity: unknown
ssb  rsa2048/XXXXXXXXXXXXXXXX
     created: 2019-05-28  expires: never       usage: E   
[ unknown] (1). Your Name <your email at xwiki.com>

gpg> trust
sec  rsa2048/XXXXXXXXXXXXXXXX
     created: 2019-05-28  expires: never       usage: SC  
     trust: unknown       validity: unknown
ssb  rsa2048/XXXXXXXXXXXXXXXX
     created: 2019-05-28  expires: never       usage: E   
[ unknown] (1). Your Name <your email at xwiki.com>

Please decide how far you trust this user to correctly verify other users' keys
(by looking at passports, checking fingerprints from different sources, etc.)

  1 = I don't know or won't say
  2 = I do NOT trust
  3 = I trust marginally
  4 = I trust fully
  5 = I trust ultimately
  m = back to the main menu

Your decision? 5
Do you really want to set this key to ultimate trust? (y/N) y

sec  rsa2048/XXXXXXXXXXXXXXXX
     created: 2019-05-28  expires: never       usage: SC  
     trust: ultimate      validity: unknown
ssb  rsa2048/XXXXXXXXXXXXXXXX
     created: 2019-05-28  expires: never       usage: E   
[ unknown] (1). Your Name <your email at xwiki.com>
Please note that the shown key validity is not necessarily correct
unless you restart the program.

gpg> save
Key not changed so no update needed.
you@yourMachine:~ % 
```


