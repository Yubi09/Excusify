let currentExcuseId = null;
let currentExcuseText = null; // Renamed for clarity, matches backend
let currentScenario = null;
let currentUserRole = null; // Stored for pre-filling saved excuses
let currentRecipient = null; // Stored for pre-filling saved excuses
let currentLanguage = 'en'; // Store the language of the generated excuse for speaking/saving

// Helper function for title casing
function toTitleCase(str) {
  if (!str) return '';
  return str
    .replace(/_/g, ' ')
    .split(' ')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

// Get DOM elements
const believabilityRange = document.getElementById('believability');
const believabilityValueSpan = document.getElementById('believability_value');
const generateExcuseBtn = document.getElementById('generateExcuseBtn');
const excuseOutputDiv = document.getElementById('excuseOutput');
const speakExcuseBtn = document.getElementById('speakExcuseBtn');
const saveExcuseBtn = document.getElementById('saveExcuseBtn'); // New save button
const excuseAudio = document.getElementById('excuseAudio');
const effectiveBtn = document.getElementById('effectiveBtn');
const ineffectiveBtn = document.getElementById('ineffectiveBtn');
const proofTypeSelect = document.getElementById('proof_type');
const generateProofBtn = document.getElementById('generateProofBtn');
const proofOutputDiv = document.getElementById('proofOutput');
const feedbackGroup = document.querySelector('.feedback-group');
const proofSection = document.querySelector('.proof-section');
const topExcusesList = document.getElementById('topExcusesList');
const predictedNeedList = document.getElementById('predictedNeedList');
const savedExcusesList = document.getElementById('savedExcusesList'); // New list for saved excuses

// Update believability value display
believabilityRange.addEventListener('input', function () {
  believabilityValueSpan.textContent = this.value;
});

// Event Listeners for buttons
generateExcuseBtn.addEventListener('click', generateExcuse);
speakExcuseBtn.addEventListener('click', speakExcuse);
saveExcuseBtn.addEventListener('click', saveExcuse); // New event listener for save button
effectiveBtn.addEventListener('click', () => submitFeedback(true));
ineffectiveBtn.addEventListener('click', () => submitFeedback(false));
generateProofBtn.addEventListener('click', generateProof);

// Function to handle playing the excuse audio
async function speakExcuse() {
  if (!currentExcuseText || !currentExcuseId) {
    console.error('No excuse text or ID available to play.');
    alert('Please generate an excuse first.');
    return;
  }

  speakExcuseBtn.disabled = true;
  const originalButtonHtml = speakExcuseBtn.innerHTML;
  speakExcuseBtn.innerHTML =
    '<div class="spinner spinner-small"></div> Generating Audio...';
  excuseAudio.style.display = 'none';

  try {
    const response = await fetch('/speak_excuse', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        excuse: currentExcuseText,
        excuse_id: currentExcuseId,
        language: currentLanguage, // Pass language for gTTS
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! Status: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const audioUrl = data.audio_url;

    if (audioUrl) {
      excuseAudio.src = audioUrl;
      excuseAudio.load();
      excuseAudio.play();
      excuseAudio.style.display = 'block';
    } else {
      console.error('Audio URL not received.');
      alert('Error: Audio URL not received. Please try again.');
    }
  } catch (error) {
    console.error('Error generating or playing audio:', error);
    alert('Error generating or playing audio. Please try again.');
  } finally {
    speakExcuseBtn.innerHTML = originalButtonHtml;
    speakExcuseBtn.disabled = false;
  }
}

async function generateExcuse() {
  const scenario = document.getElementById('scenario').value;
  const user_role = document.getElementById('user_role').value;
  const recipient = document.getElementById('recipient').value;
  const urgency = document.getElementById('urgency').value;
  const believability = believabilityRange.value;
  const language = document.getElementById('language').value;

  // Store these values globally for use by speak, save, and proof functions
  currentScenario = scenario;
  currentUserRole = user_role;
  currentRecipient = recipient;
  currentLanguage = language;

  // Reset UI elements
  excuseOutputDiv.innerHTML = '';
  speakExcuseBtn.style.display = 'none';
  saveExcuseBtn.style.display = 'none'; // Hide save button until generated
  excuseAudio.style.display = 'none';
  excuseAudio.src = '';
  feedbackGroup.style.display = 'none';
  proofSection.style.display = 'none';
  proofOutputDiv.style.display = 'none';
  proofOutputDiv.innerHTML = '';

  // Show loading state
  excuseOutputDiv.classList.add('generating');
  excuseOutputDiv.innerHTML =
    '<div class="spinner"></div><p>Generating excuse...</p>';
  generateExcuseBtn.disabled = true;
  generateExcuseBtn.innerHTML =
    '<div class="spinner spinner-small"></div> Generating...';

  try {
    const response = await fetch('/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        scenario,
        user_role,
        recipient,
        urgency,
        believability,
        language,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    console.log('Excuse response:', data);

    currentExcuseId = data.excuse_id;
    currentExcuseText = data.excuse; // Use currentExcuseText consistently

    excuseOutputDiv.classList.remove('generating');
    excuseOutputDiv.innerHTML = `<b>Excuse:</b> ${data.excuse}`;

    // Show action buttons
    speakExcuseBtn.style.display = 'inline-block';
    saveExcuseBtn.style.display = 'inline-block'; // Show save button
    feedbackGroup.style.display = 'flex';
    proofSection.style.display = 'block';

    // Fetch and display updated insights (after a new excuse is generated)
    fetchInsights();
  } catch (error) {
    excuseOutputDiv.classList.remove('generating');
    excuseOutputDiv.innerHTML = `<p class="error-message">Error: Failed to generate excuse. Please try again.</p>`;
    console.error('Excuse generation error:', error);
  } finally {
    generateExcuseBtn.disabled = false;
    generateExcuseBtn.innerHTML = 'Generate Excuse';
  }
}

async function generateProof() {
  if (!currentExcuseId || !currentScenario || !currentExcuseText) {
    proofOutputDiv.style.display = 'block';
    proofOutputDiv.innerHTML =
      '<p class="error-message">Error: Please generate an excuse first.</p>';
    return;
  }
  const proof_type = proofTypeSelect.value;
  proofOutputDiv.style.display = 'block';

  generateProofBtn.disabled = true;
  generateProofBtn.innerHTML =
    '<div class="spinner spinner-small"></div> Generating...';

  proofOutputDiv.innerHTML =
    '<div class="spinner"></div><p>Generating proof...</p>';

  try {
    const response = await fetch(`/generate_proof/${currentExcuseId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        excuse: currentExcuseText,
        scenario: currentScenario,
        proof_type,
      }),
    });
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }
    const data = await response.json();
    console.log('Proof response:', data);
    if (data.error) {
      proofOutputDiv.innerHTML = `<p class="error-message">Error: ${data.error}</p>`;
      return;
    }

    const downloadUrl = data.proof_url;
    const filename = downloadUrl.split('/').pop();

    let downloadMessage = `<p>Proof generated: <a href="${downloadUrl}" target="_blank" download="${filename}" class="proof-link">⬇ Download ${toTitleCase(
      proof_type
    )}</a></p>`;

    if (proof_type === 'doctor_note') {
      downloadMessage += `<small>If the PDF opens in your browser instead of downloading, right-click the link and choose "Save link as..." or "Download linked file".</small>`;
    } else if (proof_type === 'chat_screenshot') {
      downloadMessage += `<small>Your PNG should download automatically. If not, right-click the link and choose "Save link as...".</small>`;
    } else if (proof_type === 'location_log') {
      downloadMessage += `<small>Your JSON should download automatically. If not, right-click the link and choose "Save link as...".</small>`;
    }

    proofOutputDiv.innerHTML = downloadMessage;
  } catch (error) {
    proofOutputDiv.innerHTML = `<p class="error-message">Error: Failed to generate proof. Please try again.</p>`;
    console.error('Proof generation error:', error);
  } finally {
    generateProofBtn.disabled = false;
    generateProofBtn.innerHTML = 'Generate Proof';
  }
}

// Function to submit feedback
async function submitFeedback(isEffective) {
  if (!currentExcuseId) {
    alert('Please generate an excuse before submitting feedback.');
    return;
  }

  try {
    const response = await fetch('/feedback', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        excuse_id: currentExcuseId,
        is_effective: isEffective,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! Status: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    console.log('Feedback submitted:', data);
    alert('Thank you for your feedback!');

    // Optionally hide feedback buttons after submission
    feedbackGroup.style.display = 'none';

    // Refresh insights after feedback
    fetchInsights();
  } catch (error) {
    console.error('Error submitting feedback:', error);
    alert('Error submitting feedback. Please try again.');
  }
}

// Function to fetch and display AI Insights
async function fetchInsights() {
  topExcusesList.innerHTML =
    '<div class="spinner spinner-small"></div> Loading insights...';
  predictedNeedList.innerHTML = ''; // Clear for new content

  try {
    const response = await fetch('/insights');
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! Status: ${response.status} - ${errorText}`);
    }
    const insights = await response.json();
    console.log('AI Insights:', insights);

    // Populate Top Excuses
    if (insights.top_excuses && insights.top_excuses.length > 0) {
      topExcusesList.innerHTML = ''; // Clear loading message
      insights.top_excuses.forEach((excuse) => {
        const li = document.createElement('li');
        const effectiveness =
          excuse.total_feedback > 0
            ? `${(
                (excuse.effective_count / excuse.total_feedback) *
                100
              ).toFixed(0)}% Effective`
            : 'No feedback yet';
        li.innerHTML = `"${excuse.excuse_text}" <br><small>(${effectiveness} from ${excuse.total_feedback} feedback)</small>`;
        topExcusesList.appendChild(li);
      });
    } else {
      topExcusesList.innerHTML =
        '<p>No feedback collected yet to rank excuses.</p>';
    }

    // Populate Predicted Excuse Need
    let predictedHtml = '';

    if (
      insights.frequent_scenarios_all_time &&
      insights.frequent_scenarios_all_time.length > 0
    ) {
      predictedHtml += '<h4>Frequently Needed Scenarios:</h4><ul>';
      insights.frequent_scenarios_all_time.forEach((scenario) => {
        predictedHtml += `<li>${toTitleCase(scenario.scenario)}: ${
          scenario.count
        } times</li>`;
      });
      predictedHtml += '</ul>';
    } else {
      predictedHtml += '<p>No recent scenario data.</p>';
    }

    if (insights.predicted_excuse_time) {
      predictedHtml += `<p><strong>Historical busiest time:</strong> ${insights.predicted_excuse_time}</p>`;
    }

    predictedNeedList.innerHTML = predictedHtml;
  } catch (error) {
    console.error('Error fetching AI insights:', error);
    topExcusesList.innerHTML =
      '<p class="error-message">Failed to load insights.</p>';
    predictedNeedList.innerHTML = '';
  }
}

// --- NEW: Saved Excuses Functions ---

// Function to handle saving an excuse
async function saveExcuse() {
  if (!currentExcuseText) {
    alert('No excuse to save. Please generate one first.');
    return;
  }

  try {
    const response = await fetch('/save_excuse', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        excuse_text: currentExcuseText,
        scenario: currentScenario,
        user_role: currentUserRole,
        recipient: currentRecipient,
        language: currentLanguage,
      }),
    });
    const data = await response.json();
    if (response.ok) {
      alert(data.message);
      loadSavedExcuses(); // Reload saved excuses list after saving
    } else {
      alert(`Error saving excuse: ${data.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error saving excuse:', error);
    alert('Failed to save excuse.');
  }
}

// Function to load and display saved excuses
async function loadSavedExcuses() {
  try {
    const response = await fetch('/get_saved_excuses');
    const savedExcuses = await response.json();

    savedExcusesList.innerHTML = ''; // Clear current list

    if (savedExcuses.length === 0) {
      savedExcusesList.innerHTML =
        '<p>No saved excuses yet. Generate and save one!</p>';
      return;
    }

    // Sort by saved_at timestamp, newest first
    savedExcuses.sort((a, b) => new Date(b.saved_at) - new Date(a.saved_at));

    savedExcuses.forEach((excuse) => {
      const excuseDiv = document.createElement('div');
      excuseDiv.classList.add('saved-excuse-item');
      const savedDate = new Date(excuse.saved_at);
      const formattedDate = savedDate.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });

      excuseDiv.innerHTML = `
                <p><strong>Scenario:</strong> ${toTitleCase(
                  excuse.scenario
                )}</p>
                <p>${excuse.excuse_text}</p>
                <p class="saved-date">Saved: ${formattedDate}</p>
                <div class="saved-excuse-actions">
                    <button class="use-saved-btn btn btn-secondary" data-id="${
                      excuse.id
                    }">Use This</button>
                    <button class="delete-saved-btn btn btn-danger" data-id="${
                      excuse.id
                    }">Delete</button>
                </div>
            `;
      savedExcusesList.appendChild(excuseDiv);
    });

    // Add event listeners to the new "Use" and "Delete" buttons
    document.querySelectorAll('.use-saved-btn').forEach((button) => {
      button.addEventListener('click', (event) =>
        useSavedExcuse(event.target.dataset.id, savedExcuses)
      );
    });

    document.querySelectorAll('.delete-saved-btn').forEach((button) => {
      button.addEventListener('click', (event) =>
        deleteSavedExcuse(event.target.dataset.id)
      );
    });
  } catch (error) {
    console.error('Error loading saved excuses:', error);
    savedExcusesList.innerHTML =
      '<p class="error-message">Failed to load saved excuses.</p>';
  }
}

// Function to use a saved excuse (pre-fill the form and display)
function useSavedExcuse(id, savedExcuses) {
  const excuseToUse = savedExcuses.find((exc) => exc.id === id);
  if (excuseToUse) {
    // Pre-fill the form fields
    document.getElementById('scenario').value = excuseToUse.scenario;
    document.getElementById('user_role').value = excuseToUse.user_role;
    document.getElementById('recipient').value = excuseToUse.recipient;
    document.getElementById('language').value = excuseToUse.language;
    // Urgency/Believability aren't stored, so they remain as current selections or defaults

    // Display the excuse text in the output area
    excuseOutputDiv.innerHTML = `<b>Excuse:</b> ${excuseToUse.excuse_text}`;
    currentExcuseText = excuseToUse.excuse_text;
    // When using a saved excuse, it's not a *newly generated* one, so clear currentExcuseId
    // This means feedback won't apply directly to the *saved* item, only newly generated ones.
    currentExcuseId = null;
    currentScenario = excuseToUse.scenario;
    currentUserRole = excuseToUse.user_role;
    currentRecipient = excuseToUse.recipient;
    currentLanguage = excuseToUse.language;

    // Ensure action buttons are visible for the displayed excuse
    speakExcuseBtn.style.display = 'inline-block';
    saveExcuseBtn.style.display = 'none'; // Cannot "save" an already saved excuse
    feedbackGroup.style.display = 'none'; // No feedback for used saved excuses
    proofSection.style.display = 'block'; // Can still generate proof based on this excuse
    proofOutputDiv.style.display = 'none';
    proofOutputDiv.innerHTML = '';

    alert(
      'Form pre-filled with saved excuse! You can now speak it or generate proof for it.'
    );
  } else {
    alert('Saved excuse not found.');
  }
}

// Function to delete a saved excuse
async function deleteSavedExcuse(id) {
  if (
    !confirm(
      'Are you sure you want to delete this saved excuse? This action cannot be undone.'
    )
  ) {
    return;
  }

  try {
    const response = await fetch(`/delete_saved_excuse/${id}`, {
      method: 'DELETE',
    });
    const data = await response.json();
    if (response.ok) {
      alert(data.message);
      loadSavedExcuses(); // Reload the list after deletion
    } else {
      alert(`Error deleting excuse: ${data.error || 'Unknown error'}`);
    }
  } catch (error) {
    console.error('Error deleting excuse:', error);
    alert('Failed to delete excuse.');
  }
}

// Initial load: Fetch insights and load saved excuses when the DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  believabilityValueSpan.textContent = believabilityRange.value; // Set initial value for slider
  fetchInsights();
  loadSavedExcuses(); // Load saved excuses on page load
});
