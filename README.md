# Passbolt Toolbox

This tools provides various functionalities around a Passbolt instance, the main one being its capacity to ease
the automated renewal of passwords.

## Technical overview

On its first start, the tool will create a directory `~/.password-toolbox` storing all of its configuration, this includes :
* The tool configuration
* The GnuPG keyring used by the tool

In order to properly communicate with Passbolt, the tool needs to know the following information :
* The public key of the Passbolt server (this key should be trusted *ultimately* by GnuPG)
* The private key of the user that you will use for authentication on the server (this key should also be *ultimately* trusted)
* The address of the server

Those information are stored in `~/.passbolt-toolbox/config.json`. You can refer to this file in case something goes wrong. Here is an example a file :

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
git clone https://github.com/xwikisas/passbolt-toolbox.git
cd passbolt-toolbox
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

You can run `passbolt-toolbox setup` to start the setup of the server. If a server was previously set up, the tool will ask before overwriting the server configuration.

> In case your server is configured with HTTPS but does not provide its [certificate chain](https://support.dnsimple.com/articles/what-is-ssl-certificate-chain/), you will need to answer YES to the question `Trust the server certficate without verification ?`.

This option will simply get the fingerprint of the server and its public key for you and import it in the tool keyring.

#### User configuration

This part is not automated yet :/ however, it's supposed to be more simple than the server part. Before continuing, make sure that you have a local copy of your Passbolt private key.

First, import your key in the application keyring :
```
gpg --homedir ~/.passbolt-toolbox/gnupg --import <your_file>
```

You can now see your imported key with `gpg --homedir ~/.passbolt-toolbox/gnupg --list-secret-keys`, here is an example :
```
~/.passbolt-toolbox/gnupg/pubring.gpg
------------------------------------------------
sec   rsa2048 2019-05-28 [SC]
      XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
uid           [ unknown] Your Name <your email at xwiki.com>
ssb   rsa2048 2019-05-28 [E]
```

Then, you will need to copy-paste your key fingerprint in the `user.fingerprint` field of `~/.passbolt-toolbox/config.json`.

### Testing the configuration

Once everything is done, you can validate your configuration by running :
```
passbolt-toolbox test
```

This will simply test the authentication on the Passbolt server.
