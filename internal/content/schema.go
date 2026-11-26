package content

import (
	"bytes"
	"encoding/json"
	"fmt"

	"github.com/santhosh-tekuri/jsonschema/v6"
)

func ValidateSchema(records []Record, path string) error {
	compiler := jsonschema.NewCompiler()
	schema, err := compiler.Compile(path)
	if err != nil {
		return fmt.Errorf("compile JSON Schema %s: %w", path, err)
	}
	for i, record := range records {
		encoded, err := json.Marshal(record)
		if err != nil {
			return err
		}
		instance, err := jsonschema.UnmarshalJSON(bytes.NewReader(encoded))
		if err != nil {
			return err
		}
		if err = schema.Validate(instance); err != nil {
			return fmt.Errorf("record %d (%s) does not match JSON Schema: %w", i, record.ID, err)
		}
	}
	return nil
}
