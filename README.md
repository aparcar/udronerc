# udrone - QA done right

Udrone is a system that allows you to remotely control _N_ drones. The _N_
drones can be sent a number of different commands. Based on these commands the
drone will perform a number of actions and report the result back to the drone
host controller. The system consists of a number of files on the controller
side.

## Setup

Please read the [generated documentation][docs_setup] for a development setup.

[docs_setup]: https://aparcar.github.io/udronerc/development/setup/

## Running

If the package is installed via `pip` you can access the CLI by running `udronerc`.

See basic test suites in the folder `suites/`. To run a specific suite use the following command:

```bash
udronerc suite run suites/simple.yml
```

Responses are stored in `./results.json` for further processing. Change the log level in `config.yml` to see more detailed information.