## Search and Filtering

### What is Search/Filtering?

Searching and filtering user data are essential features in many applications, allowing both administrators and users to efficiently locate specific user records based on criteria such as names, roles, email addresses, or other attributes. This functionality is crucial for managing large datasets where manual search would be impractical and time-consuming. Effective searching and filtering can enhance user experience, improve system manageability, and support data-driven decisions by enabling quick and easy access to relevant data.  

Additionally, these capabilities are integral for features like reporting, monitoring user activities, and implementing security measures based on user roles or behaviors.

### Implementation

The core search functionality is implemented in `app/services/user_service.py` under `UserService.search_users`.  

It takes two parameters `search_query` and `filter_query` of type `dict`.  

The key, value pairs passed in `search_query` are appended to `search_conditions`. Then they are passed to the query separated by `OR` operands.


The key, value pairs passed in `filter_query` are appended to `filter_conditions`. Then they are passed to the query separated by `AND` operands.

Finally, the pagination limits are applied to the query.  

### Usage

Call `UserService.search_users` with the following parameters
- `session (AsyncSession)`: The DB Session
- `search_query (dict)`: The dictionary for passing search queries
- `filter_query (dict)`:  The dictionary for passing filter queries


