# Movie Booking Agent with WhatsApp Chatbot

A conversational movie ticket booking agent integrated with **WhatsApp** using **Twilio**, powered by **LLM Gemini** for intelligent responses. Users can check available movies, showtimes, and book tickets seamlessly via chat.

## Features

- Conversational interface on WhatsApp for interacting with the agent.
- Dynamic retrieval of movie data from a **MongoDB Atlas** demo database.
- Integration with **LLM Gemini** to curate responses using a custom system prompt.
- End-to-end booking workflow: view movies → select showtime → book tickets → receive confirmation.
- Handles user queries naturally with stepwise guidance.

## Technologies Used

- **Frontend/Chat Interface:** WhatsApp (via Twilio API)
- **Backend:** Node.js, Express.js
- **Database:** MongoDB Atlas (demo dataset)
- **AI/LLM:** Gemini for natural language understanding and response curation
- **Deployment Tools:** Twilio API integration, Node.js server

## System Design

1. **User Interaction:** Users send messages on WhatsApp.
2. **Message Handling:** Messages are received via Twilio webhook and sent to the Node.js server.
3. **Query Processing:** Server passes the query to LLM Gemini with a predefined system prompt for structured response.
4. **Data Fetching:** Gemini curates the answer using movie data from MongoDB Atlas.
5. **Response Delivery:** Stepwise guidance and booking options are sent back to the user on WhatsApp.

## Demo Data

- The project currently uses a demo **MongoDB Atlas** database with sample movies, showtimes, and seats.
- The system is designed to be scalable to real-world movie booking databases.

## Setup Instructions

1. Clone the repository:  
   ```bash
   git clone <repo-url>
   cd movie-booking-agent

2. Install dependencies:
    ```bash
    npm install

3. Configure environment variables:
    ```bash
    MONGO_URI=<mongobd_uri>

    
    GOOGLE_API_KEY=<google_api_key>
    OPENAI_API_KEY=<open_api_key>

    
    EMAIL_USER=<"email_id">
    EMAIL_PASS=<"email_pass">
    SMTP_HOST=<"smtp_host">
    SMTP_PORT=<port_number>
    SMTP_STARTTLS=true

    
    TWILIO_ACCOUNT_SID=<>
    TWILIO_AUTH_TOKEN=<>
    TWILIO_WHATSAPP_NUMBER=<> 


## Future Enhancements

- Add real payment gateway integration for ticket booking.
- Implement seat selection with real-time availability.
- Extend to multiple theaters and cities.
- Add multi-language support for a wider audience.



