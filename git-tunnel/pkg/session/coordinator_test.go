package session

import (
	"testing"
)

func TestNewCoordinator(t *testing.T) {
	coord := NewCoordinator(false, "my_super_secret_session_key")
	if coord == nil {
		t.Fatal("expected coordinator to be initialized")
	}

	fingerprint := coord.Fingerprint()
	if fingerprint == "" {
		t.Error("expected human-verifiable fingerprint to be generated")
	}
}

func TestBufferPooling(t *testing.T) {
	coord := NewCoordinator(false, "")

	// Test 4KB pool
	buf4 := coord.GetBuffer(2048)
	if len(buf4) != 2048 {
		t.Errorf("expected buffer of length 2048, got %d", len(buf4))
	}
	if cap(buf4) != 4096 {
		t.Errorf("expected buffer capacity of 4096, got %d", cap(buf4))
	}
	coord.PutBuffer(buf4)

	// Test 16KB pool
	buf16 := coord.GetBuffer(10000)
	if len(buf16) != 10000 {
		t.Errorf("expected buffer of length 10000, got %d", len(buf16))
	}
	if cap(buf16) != 16384 {
		t.Errorf("expected buffer capacity of 16384, got %d", cap(buf16))
	}
	coord.PutBuffer(buf16)
}

func TestSecretsDenylist(t *testing.T) {
	coord := NewCoordinator(false, "")

	blockedPaths := []string{
		".env",
		"sub/folder/.env",
		"id_rsa",
		"aws_credentials",
		"/etc/ssh/id_rsa",
	}

	for _, path := range blockedPaths {
		if !coord.IsBlockedPath(path) {
			t.Errorf("expected path %s to be blocked", path)
		}
	}

	allowedPaths := []string{
		"main.go",
		"pkg/session/coordinator.go",
		"README.md",
	}

	for _, path := range allowedPaths {
		if coord.IsBlockedPath(path) {
			t.Errorf("expected path %s to be allowed", path)
		}
	}
}
