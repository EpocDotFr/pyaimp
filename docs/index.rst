PyAIMP documentation
====================

Welcome! This documentation is about PyAIMP, a Python `AIMP <http://www.aimp.ru/>`_ remote API wrapper.

PyAIMP comes as a simple Python module that covers 100% of the AIMP remote API features with the help of `pywin32 <https://pypi.python.org/pypi/pypiwin32>`_ (the only dependency).

Prerequisites
-------------

Should work on any Python 3.x version. Feel free to test with another Python version and give me feedback.

Installation
------------

The usual way:

.. code-block:: console

    $ pip install pyaimp

The McGyver way, after cloning/downloading this repo:

.. code-block:: console

    $ python setup.py install

Usage
-----

Create a :class:`pyaimp.Client` instance and you are ready to use any of its public methods.

Example displaying the current playback status:

.. code-block:: python

    import pyaimp

    try:
        player = pyaimp.Client()

        status = player.get_player_state()

        if status == pyaimp.PlayerState.Stopped:
            print('AIMP actually doesn\'t play anything')
        elif status == pyaimp.PlayerState.Paused:
            print('AIMP is taking a break')
        elif status == pyaimp.PlayerState.Playing:
            print('Rock \'n Roll baby)
    except RuntimeError as re: # AIMP instance not found
        print(re)

Continue reading below to know about what you can do.

API docs
--------

.. automodule:: pyaimp
   :members:
   :undoc-members: