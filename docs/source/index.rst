.. image:: https://www.gstatic.com/buganizer/img/v0/logo.svg
   :alt: logo
   :width: 150
   :height: 150
   :align: center

.. centered:: Python client for the Google Issue Tracking system (Buganizer)

Quick Start
-----------

.. code-block:: python

   from buganize import Buganize


   async def main():
       async with Buganize() as client:
           result = await client.search(query="status:open priority:p1", page_size=25)
           for issue in result.issues:
               print(f"#{issue.id} [{issue.status.name}] {issue.title}")

.. code-block:: bash

   buganize search "status:open priority:p1"

.. toctree::
   :hidden:

   installation
   usage
   api
   audit
