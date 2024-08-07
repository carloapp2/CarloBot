# CarloBot
CarloBot is a Personal Assistant for Carlo that uses Generative AI.

https://www.linkedin.com/in/carloappugliese/

https://www.youtube.com/@GenAI4Biz

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
   BOTNAME=<name-of-the-assistant>
   FULLNAME=<name-of-person-whom-the-bot-is-representing>
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

6. **Change Assistant Image**:
   Update the current `static/bot.png` image to reflect your preferred picture for the assistant. Ensure that your chosen image is in PNG format and named `bot.png` for seamless integration.

7. **Change Default Questions**:
   Update the current `default_questions.txt` file with the questions that you want to display on the UI.

8. **Start the Application**:
   Launch the application with:
   ```bash
   python app.py
   ```

Your personal assistant is now ready to use! Access it through [http://127.0.0.1:5001](http://127.0.0.1:5001).

Admin users can access additional functionalities via [http://127.0.0.1:5001/add_to_kb](http://127.0.0.1:5001/add_to_kb) to enrich the knowledge base.
