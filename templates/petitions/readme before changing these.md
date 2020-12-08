These are files that you _may_ want to use in the application. The Django app and CLI don't actually look here to find petition templates.

If you want to use these templates in the app, you need to upload them to the app, and the app will take care of storing them.

# Large File Storage

These .docx files are stored using git-large-file-storage, or git-lfs.

So before you make any changes to them, make sure you've got git-lfs installed. See https://git-lfs.github.com/.

If you change these without having git-lfs installed, you may cause errors in the repository that will be hard to fix!
