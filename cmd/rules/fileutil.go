package main

import (
	"os"
	"path/filepath"
)

func atomicWriteFile(path string, data []byte, mode os.FileMode) error {
	directory := filepath.Dir(path)
	if err := os.MkdirAll(directory, 0755); err != nil {
		return err
	}
	temporary, err := os.CreateTemp(directory, ".rules-*.tmp")
	if err != nil {
		return err
	}
	tempName := temporary.Name()
	defer os.Remove(tempName)
	if _, err = temporary.Write(data); err != nil {
		_ = temporary.Close()
		return err
	}
	if err = temporary.Chmod(mode); err != nil {
		_ = temporary.Close()
		return err
	}
	if err = temporary.Close(); err != nil {
		return err
	}
	if err = os.Rename(tempName, path); err == nil {
		return nil
	}
	// Windows does not replace an existing destination with Rename; keep a recoverable backup.
	backup := path + ".bak"
	_ = os.Remove(backup)
	if _, statErr := os.Stat(path); statErr != nil {
		return err
	}
	if moveErr := os.Rename(path, backup); moveErr != nil {
		return moveErr
	}
	if moveErr := os.Rename(tempName, path); moveErr != nil {
		_ = os.Rename(backup, path)
		return moveErr
	}
	_ = os.Remove(backup)
	return nil
}
