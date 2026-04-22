from pydantic import create_model

def generate_dynamic_schema(user_fields: list):
    """
    Converts a list of strings like ['Price', 'Address'] 
    into a formal Pydantic Model the AI understands.
    """
    # We tell Pydantic: every field the user wants should be a string
    field_definitions = {field: (str, ...) for field in user_fields}
    
    # Create the class on the fly
    DynamicModel = create_model("UserDefinedSchema", **field_definitions)
    return DynamicModel