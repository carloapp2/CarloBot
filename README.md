# CarloBot
CarloBot is a Personal Assistant for Carlo that uses Generative AI.

## Setup Instructions

Follow these steps to set up your personal assistant:


1. **Organize Your Data**: 
   Copy all your data into the designated `data` folder. Ensure files are in either `.txt` or `.pdf` format.

2. **Configuration**:
   Create a `.env` file in the root directory and populate it with the following information:
   ```dotenv
   WATSONX_APIKEY=<your-watsonx-api-key>
   PROJECT_ID=<watsonx-project-id>
   IBM_CLOUD_URL=https://us-south.ml.cloud.ibm.com
   USERNAME=<username-for-admin-access>
   PASSWORD=<password-for-admin-access>
   ```
3. **Set Up Python Virtual Environment**:
   Create a Python virtual environment using the command:
   ```bash
   python -m venv personal_bot
   ```
4. **Activate Virtual Environment**:
   Depending on your operating system, activate the virtual environment:
   - Windows:
     ```bash
     personal_bot\Scripts\activate
     ```
   - Linux and macOS:
     ```bash
     source personal_bot/bin/activate
     ```

5. **Install Dependencies**:
   Install all required dependencies using:
   ```bash
   pip install -r requirements.txt
   ```
6. **Start the Application**:
   Launch the CarloBot application with:
   ```bash
   python app.py
   ```

Your personal assistant is now ready to use! Access it through [http://127.0.0.1:5001](http://127.0.0.1:5001).

Admin users can access additional functionalities via [http://127.0.0.1:5001/add_to_kb](http://127.0.0.1:5001/add_to_kb) to enrich the knowledge base.