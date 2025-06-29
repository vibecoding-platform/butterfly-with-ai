// Log Monitor Debug Script
// Run this in the browser console to debug the log monitor tab

console.log('🔍 Log Monitor Debug Script Started');

// Check if the tab store is available
const checkTabStore = () => {
  try {
    const app = document.querySelector('#app').__vueApp__;
    if (app) {
      console.log('✅ Vue app found');
      
      // Try to access the tab store
      const stores = app.config.globalProperties.$pinia?.state?.value;
      console.log('📦 Available stores:', Object.keys(stores || {}));
      
      // Check for terminal tab store
      if (stores?.terminalTab) {
        const tabStore = stores.terminalTab;
        console.log('🗂️ Terminal Tab Store state:', {
          tabs: tabStore.tabs,
          activeTabId: tabStore.activeTabId,
          activeTabs: tabStore.tabs?.filter(tab => tab.isActive)
        });
        
        // Check if log monitor tab exists
        const logMonitorTabs = tabStore.tabs?.filter(tab => tab.type === 'log-monitor');
        console.log('📈 Log Monitor tabs:', logMonitorTabs);
        
        return tabStore;
      } else {
        console.warn('⚠️ Terminal tab store not found');
      }
    }
  } catch (error) {
    console.error('❌ Error accessing Vue app:', error);
  }
  return null;
};

// Check DOM elements
const checkDOMElements = () => {
  console.log('\n🔍 Checking DOM elements...');
  
  // Check for tab bar
  const tabBar = document.querySelector('.terminal-tab-bar');
  console.log('📊 Tab bar element:', tabBar ? '✅ Found' : '❌ Not found');
  
  // Check for fixed log monitor tab
  const fixedLogTab = document.querySelector('.log-monitor-tab.fixed-tab');
  console.log('🔧 Fixed log monitor tab:', fixedLogTab ? '✅ Found' : '❌ Not found');
  
  // Check for all tabs
  const allTabs = document.querySelectorAll('.terminal-tab');
  console.log('📑 All tabs found:', allTabs.length);
  allTabs.forEach((tab, index) => {
    console.log(`  Tab ${index + 1}:`, {
      classes: tab.className,
      text: tab.textContent?.trim(),
      visible: tab.style.display !== 'none'
    });
  });
  
  // Check for log monitor content
  const logMonitorContent = document.querySelector('.log-monitor-tab-content');
  console.log('📋 Log monitor content:', logMonitorContent ? '✅ Found' : '❌ Not found');
  
  if (logMonitorContent) {
    console.log('📄 Log monitor content visible:', logMonitorContent.style.display !== 'none');
  }
  
  // Check for TerminalLogMonitorPanel component
  const logMonitorPanel = document.querySelector('.terminal-log-monitor-panel');
  console.log('🎛️ Log monitor panel:', logMonitorPanel ? '✅ Found' : '❌ Not found');
};

// Create log monitor tab programmatically
const createLogMonitorTab = () => {
  try {
    const app = document.querySelector('#app').__vueApp__;
    const stores = app.config.globalProperties.$pinia?.state?.value;
    
    if (stores?.terminalTab) {
      const tabStore = stores.terminalTab;
      
      // Call the createLogMonitorTab method
      console.log('🔄 Creating log monitor tab...');
      
      // Simulate the method call (this needs to be done properly through Vue reactivity)
      console.log('💡 To create a log monitor tab, click the "+" button and select "Log Monitor"');
      console.log('💡 Or click the fixed log monitor tab in the tab bar');
      
      return true;
    }
  } catch (error) {
    console.error('❌ Error creating log monitor tab:', error);
  }
  return false;
};

// Test the tab switching
const testTabSwitching = () => {
  console.log('\n🔄 Testing tab switching...');
  
  // Find and click the fixed log monitor tab
  const fixedLogTab = document.querySelector('.log-monitor-tab.fixed-tab');
  if (fixedLogTab) {
    console.log('🖱️ Clicking fixed log monitor tab...');
    fixedLogTab.click();
    
    setTimeout(() => {
      const isActive = fixedLogTab.classList.contains('active');
      console.log('📈 Log monitor tab active:', isActive ? '✅ Yes' : '❌ No');
      
      // Check if content is visible
      const content = document.querySelector('.log-monitor-tab-content');
      if (content) {
        const isVisible = content.offsetParent !== null;
        console.log('👁️ Log monitor content visible:', isVisible ? '✅ Yes' : '❌ No');
      }
    }, 100);
  } else {
    console.log('❌ Fixed log monitor tab not found');
  }
};

// Run all checks
const runFullDiagnostic = () => {
  console.log('🚀 Starting full log monitor diagnostic...\n');
  
  const tabStore = checkTabStore();
  checkDOMElements();
  
  if (tabStore) {
    console.log('\n💡 Store methods available:');
    console.log('- To create log monitor tab: tabStore.createLogMonitorTab()');
    console.log('- To switch to a tab: tabStore.switchToTab(tabId)');
  }
  
  // Test clicking after a short delay
  setTimeout(testTabSwitching, 1000);
  
  console.log('\n✅ Diagnostic complete. Check the results above.');
};

// Export functions for manual testing
window.logMonitorDebug = {
  checkTabStore,
  checkDOMElements,
  createLogMonitorTab,
  testTabSwitching,
  runFullDiagnostic
};

console.log('🎯 Debug functions available as window.logMonitorDebug');
console.log('🔧 Run window.logMonitorDebug.runFullDiagnostic() for full check');

// Auto-run diagnostic
runFullDiagnostic();