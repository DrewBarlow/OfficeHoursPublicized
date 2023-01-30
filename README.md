## Office Hours Bot
### Intended to be used in academic discord servers

#### NOTE: THIS IS REPOSITORY USES AN OUTDATED API AND IS NO LONGER MAINTAINED!

##### To run:
  1. Clone this repository
  2. Get your own bot token from [discord's developer portal](https://discord.com/login?redirect_to=%2Fdevelopers%2Fapplications)
  3. Invite your bot to the server of your choosing
  4. Give teaching assistants the "Handler" role and students the "Queueable" role
  5. Run `main.py`
  
##### Commands:
  * For handlers:
      * !currqueue/!currq/!cq
          * Shows the queue of students in this guild
      * !accept/!take/!yoink
          * Accepts the next student in the queue, generating a category for the session
      * !close/!finish/!finishup/!finished/!done
          * Closes the current session and cleans the category, if there is one
      * !onduty/!on
          * Gives the handler an "On Duty" role
          * The server then allows for students to enter the queue, if no handlers were previously on duty
      * !offduty/!off
          * Removes the "On Duty" role from the handler
          * Disables queueing if no handlers are left on duty
      * !kick/!boot/!remove <n:int>
          * Removes the nth student from the queue
  * For students:
      * !enqueue/!queue/!request/!q <reason:str>
          * Places the student into this guild's queue
      * !dequeue/!leave!leavequeue
          * Gives the student the option to leave the queue on their own accord
