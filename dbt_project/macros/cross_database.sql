{% macro date_from_timestamp(expression) -%}
cast({{ expression }} as date)
{%- endmacro %}

{% macro timestamp_literal(value) -%}
cast('{{ value }}' as timestamp)
{%- endmacro %}

{% macro as_double(expression) -%}
cast({{ expression }} as double)
{%- endmacro %}

{% macro percentile_value(expression, percentile) -%}
{% if target.type == 'trino' -%}
approx_percentile({{ expression }}, {{ percentile }})
{%- else -%}
quantile_cont({{ expression }}, {{ percentile }})
{%- endif %}
{%- endmacro %}

{% macro trino_s3_properties(model_name) -%}
{% if target.type == 'trino' -%}
{{ return({'format': "'PARQUET'", 'external_location': "'s3://data-lakehouse/analytics/" ~ model_name ~ "'"}) }}
{%- else -%}
{{ return(none) }}
{%- endif %}
{%- endmacro %}
