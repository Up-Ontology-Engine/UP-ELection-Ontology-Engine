import sys
from pathlib import Path

# Add backend directory to path to import schemas
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.schemas import (
    HealthResponse, CandidateResponse, SchemeResponse,
    ConversionOverviewResponse, BoothGeoResponse, IntelSummaryResponse
)

def pydantic_to_ts(model) -> str:
    """Converts a Pydantic model to a TypeScript interface string."""
    name = model.__name__
    lines = [f"export interface {name} {{"]
    
    # Retrieve field definitions
    for field_name, field in model.model_fields.items():
        annotation = field.annotation
        is_optional = False
        
        # Check for Optional or Union[..., None]
        # Basic check for Optional (Union)
        if hasattr(annotation, "__origin__") and annotation.__origin__ is UnionType or str(annotation).startswith("typing.Union") or str(annotation).startswith("typing.Optional"):
            is_optional = True
            # Extract internal type
            args = annotation.__args__
            args = [a for a in args if a is not type(None)]
            if len(args) == 1:
                annotation = args[0]
        
        # Map Python types to TypeScript types
        ts_type = "any"
        if annotation is str:
            ts_type = "string"
        elif annotation is int or annotation is float:
            ts_type = "number"
        elif annotation is bool:
            ts_type = "boolean"
        elif str(annotation).startswith("typing.List") or hasattr(annotation, "__origin__") and annotation.__origin__ is list:
            ts_type = "any[]"
            # Get internal type if possible
            if hasattr(annotation, "__args__") and len(annotation.__args__) > 0:
                arg = annotation.__args__[0]
                if arg is str:
                    ts_type = "string[]"
                elif arg is int or arg is float:
                    ts_type = "number[]"
                elif arg is bool:
                    ts_type = "boolean[]"
                elif hasattr(arg, "model_fields"):
                    ts_type = f"{arg.__name__}[]"
                else:
                    ts_type = "Record<string, any>[]"
        elif str(annotation).startswith("typing.Dict") or hasattr(annotation, "__origin__") and annotation.__origin__ is dict:
            ts_type = "Record<string, any>"
        elif hasattr(annotation, "model_fields"):
            ts_type = annotation.__name__
            
        opt_str = "?" if is_optional or field.default is not None and field.default != ... else ""
        lines.append(f"    {field_name}{opt_str}: {ts_type};")
        
    lines.append("}\n")
    return "\n".join(lines)

import types
UnionType = getattr(types, "UnionType", None)

def main():
    models = [
        HealthResponse, CandidateResponse, SchemeResponse,
        ConversionOverviewResponse, BoothGeoResponse, IntelSummaryResponse
    ]
    
    output_path = Path(__file__).resolve().parent.parent / "frontend" / "nextjs" / "lib" / "api-types.ts"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    ts_content = "/* eslint-disable */\n/* Auto-generated from Pydantic schemas in backend/schemas.py */\n\n"
    for model in models:
        ts_content += pydantic_to_ts(model)
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ts_content)
    print(f"Generated TypeScript interfaces at: {output_path}")

if __name__ == "__main__":
    main()
