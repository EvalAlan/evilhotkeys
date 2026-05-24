"""
Spec Activity Monitor
Tracks spec performance and actions for GUI display
"""
import time
import threading
from collections import deque
from typing import Optional, Dict, Any
from libs.logger import get_logger

logger = get_logger('spec_monitor')


class SpecMonitor:
    """Monitor and track spec activity and performance"""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.lock = threading.RLock()
        
        # Performance metrics
        self.start_time: Optional[float] = None
        self.total_keys_pressed: int = 0
        self.total_interrupts: int = 0
        self.last_key_pressed: Optional[str] = None
        self.last_key_time: Optional[float] = None
        self.last_interrupt_time: Optional[float] = None
        
        # Activity history (recent actions)
        self.action_history: deque = deque(maxlen=max_history)
        
        # Key press tracking for APM
        self.key_timestamps: deque = deque(maxlen=1000)  # Last 1000 key presses
        
        # Status
        self.is_running: bool = False
        self.current_status: str = "Idle"
        
        # Custom metrics (for spec-specific tracking)
        self.custom_metrics: Dict[str, Any] = {}
    
    def start(self):
        """Start monitoring"""
        with self.lock:
            self.start_time = time.time()
            self.is_running = True
            self.current_status = "Running"
            logger.debug("Spec monitor started")
    
    def stop(self):
        """Stop monitoring"""
        with self.lock:
            self.is_running = False
            self.current_status = "Stopped"
            logger.debug("Spec monitor stopped")
    
    def reset(self):
        """Reset all metrics"""
        with self.lock:
            self.start_time = None
            self.total_keys_pressed = 0
            self.total_interrupts = 0
            self.last_key_pressed = None
            self.last_key_time = None
            self.last_interrupt_time = None
            self.action_history.clear()
            self.key_timestamps.clear()
            self.custom_metrics.clear()
            self.current_status = "Idle"
            logger.debug("Spec monitor reset")
    
    def record_key_press(self, key: str):
        """Record a key press"""
        with self.lock:
            current_time = time.time()
            self.total_keys_pressed += 1
            self.last_key_pressed = key
            self.last_key_time = current_time
            self.key_timestamps.append(current_time)
            
            # Add to history
            self.action_history.append({
                'type': 'key_press',
                'key': key,
                'time': current_time
            })
    
    def record_interrupt(self, target: Optional[str] = None):
        """Record an interrupt"""
        with self.lock:
            current_time = time.time()
            self.total_interrupts += 1
            self.last_interrupt_time = current_time
            
            # Add to history
            self.action_history.append({
                'type': 'interrupt',
                'target': target,
                'time': current_time
            })
            
            logger.info(f"Interrupt fired! Total: {self.total_interrupts}")
    
    def record_custom_event(self, event_type: str, data: Any = None):
        """Record a custom event"""
        with self.lock:
            current_time = time.time()
            self.action_history.append({
                'type': event_type,
                'data': data,
                'time': current_time
            })
    
    def set_custom_metric(self, name: str, value: Any):
        """Set a custom metric value"""
        with self.lock:
            self.custom_metrics[name] = value
    
    def get_apm(self, window_seconds: int = 60) -> float:
        """Calculate Actions Per Minute over the given time window"""
        with self.lock:
            if not self.key_timestamps:
                return 0.0
            
            current_time = time.time()
            cutoff_time = current_time - window_seconds
            
            # Count keys in window
            recent_keys = sum(1 for ts in self.key_timestamps if ts >= cutoff_time)
            
            # Calculate APM
            actual_duration = min(window_seconds, current_time - self.start_time) if self.start_time else window_seconds
            if actual_duration > 0:
                return (recent_keys / actual_duration) * 60
            return 0.0
    
    def get_runtime(self) -> float:
        """Get total runtime in seconds"""
        with self.lock:
            if self.start_time:
                return time.time() - self.start_time
            return 0.0
    
    def get_last_action_text(self) -> str:
        """Get human-readable text of last action"""
        with self.lock:
            if not self.action_history:
                return "No actions yet"
            
            last_action = self.action_history[-1]
            action_type = last_action['type']
            
            if action_type == 'key_press':
                return f"Pressed: {last_action['key']}"
            elif action_type == 'interrupt':
                target = last_action.get('target', 'target')
                return f"Interrupted {target}!"
            else:
                return f"{action_type}"
    
    def get_recent_actions(self, count: int = 10) -> list:
        """Get recent actions as formatted strings"""
        with self.lock:
            recent = list(self.action_history)[-count:]
            formatted = []
            
            for action in reversed(recent):
                action_type = action['type']
                timestamp = time.strftime('%H:%M:%S', time.localtime(action['time']))
                
                if action_type == 'key_press':
                    formatted.append(f"[{timestamp}] Key: {action['key']}")
                elif action_type == 'interrupt':
                    target = action.get('target', 'target')
                    formatted.append(f"[{timestamp}] ⚡ INTERRUPT {target}")
                else:
                    formatted.append(f"[{timestamp}] {action_type}")
            
            return formatted
    
    def get_stats(self) -> Dict[str, Any]:
        """Get all stats as a dictionary"""
        with self.lock:
            runtime = self.get_runtime()
            
            return {
                'is_running': self.is_running,
                'status': self.current_status,
                'runtime': runtime,
                'total_keys_pressed': self.total_keys_pressed,
                'total_interrupts': self.total_interrupts,
                'apm': self.get_apm(),
                'last_key': self.last_key_pressed or 'None',
                'last_action': self.get_last_action_text(),
                'custom_metrics': self.custom_metrics.copy()
            }


# Global monitor instance
_monitor: Optional[SpecMonitor] = None


def get_monitor() -> SpecMonitor:
    """Get the global spec monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = SpecMonitor()
    return _monitor


def reset_monitor():
    """Reset the global monitor"""
    global _monitor
    _monitor = SpecMonitor()


# Convenience functions for specs to use
def record_key(key: str):
    """Record a key press (convenience function for specs)"""
    get_monitor().record_key_press(key)


def record_interrupt(target: Optional[str] = None):
    """Record an interrupt (convenience function for specs)"""
    get_monitor().record_interrupt(target)


def start_monitoring():
    """Start monitoring (convenience function)"""
    get_monitor().start()


def stop_monitoring():
    """Stop monitoring (convenience function)"""
    get_monitor().stop()

