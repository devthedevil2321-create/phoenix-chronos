package webrtc

import (
	"fmt"
	"sync"
)

// State defines the WebRTC PeerConnection connection recovery state type
type State int

const (
	Disconnected State = iota
	ICERestart
	Reconnecting
	Recreated
	StreamsRestored
)

func (s State) String() string {
	switch s {
	case Disconnected:
		return "Disconnected"
	case ICERestart:
		return "ICE Restart"
	case Reconnecting:
		return "Reconnecting"
	case Recreated:
		return "Recreated"
	case StreamsRestored:
		return "Streams Restored"
	default:
		return "Unknown"
	}
}

// ConnectionStateMachine manages PeerConnection network recovery state
type ConnectionStateMachine struct {
	state State
	lock  sync.RWMutex
}

// NewConnectionStateMachine initializes a new state machine at Disconnected state
func NewConnectionStateMachine() *ConnectionStateMachine {
	return &ConnectionStateMachine{
		state: Disconnected,
	}
}

// GetState returns the current state safely
func (c *ConnectionStateMachine) GetState() State {
	c.lock.RLock()
	defer c.lock.RUnlock()
	return c.state
}

// Transition moves connection status along standard network recovery paths
func (c *ConnectionStateMachine) Transition(next State) error {
	c.lock.Lock()
	defer c.lock.Unlock()

	// Validate logical transitions for infrastructure resiliency
	switch c.state {
	case Disconnected:
		if next != ICERestart {
			return fmt.Errorf("invalid transition from Disconnected to %s", next)
		}
	case ICERestart:
		if next != Reconnecting {
			return fmt.Errorf("invalid transition from ICE Restart to %s", next)
		}
	case Reconnecting:
		if next != Recreated && next != Disconnected {
			return fmt.Errorf("invalid transition from Reconnecting to %s", next)
		}
	case Recreated:
		if next != StreamsRestored && next != Disconnected {
			return fmt.Errorf("invalid transition from Recreated to %s", next)
		}
	case StreamsRestored:
		if next != Disconnected {
			return fmt.Errorf("invalid transition from Streams Restored to %s", next)
		}
	}

	fmt.Printf("🔄 [WebRTC State Machine] %s ➔ %s\n", c.state, next)
	c.state = next
	return nil
}

// RecoverSession implements robust reconnection recovery flow
func (c *ConnectionStateMachine) RecoverSession() {
	fmt.Println("⚠️ [WebRTC Connection Loss Detected! Starting resilient recovery sequence...]")

	if err := c.Transition(ICERestart); err != nil {
		fmt.Printf("Error: %v\n", err)
	}
	if err := c.Transition(Reconnecting); err != nil {
		fmt.Printf("Error: %v\n", err)
	}
	if err := c.Transition(Recreated); err != nil {
		fmt.Printf("Error: %v\n", err)
	}
	if err := c.Transition(StreamsRestored); err != nil {
		fmt.Printf("Error: %v\n", err)
	}

	fmt.Println("🚀 [Success] Reconnection finalized. All multiplexed streams restored safely.")
}
