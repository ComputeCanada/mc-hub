from flask import render_template

# https://www.terraform.io/docs/configuration/expressions.html#string-literals


def sanitize_expression(expression):
    if type(expression) == str:
        return expression.replace("\\", "\\\\").replace('"', '\\"')
    elif type(expression) == dict:
        return {
            sanitize_expression(k): sanitize_expression(v)
            for (k, v) in expression.items()
        }
    elif type(expression) == list:
        return [sanitize_expression(elem) for elem in expression]
    else:
        return expression


def render_hcl_template(template_name_or_list, **context):
    """
    Renders an HCL template (.tf files) from the template folder with the given context.
    """
    safe_context = {k: sanitize_expression(v) for (k, v) in context.items()}
    return render_template(template_name_or_list, **safe_context)

