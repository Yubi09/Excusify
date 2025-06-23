let currentExcuseId = null;
let currentExcuse = null;
let currentScenario = null;
let currentAudio = null; // Store the current audio object

// Helper function for title casing in JavaScript
function toTitleCase(str) {
  if (!str) return ''; // Handle empty or null strings
  return str
    .replace(/_/g, ' ') // Replace underscores with spaces
    .split(' ') // Split by spaces
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase()) // Capitalize first letter of each word
    .join(' '); // Join back with spaces
}

// Update believability value display
document.getElementById('believability').addEventListener('input', function () {
  document.getElementById('believability-value').textContent = this.value;
});

// Function to handle playing the excuse audio
async function playExcuse(excuse, excuseId) {
  if (!excuse) {
    console.error('No excuse text available to play.');
    return;
  }

  // Stop any currently playing audio
  if (currentAudio) {
    currentAudio.pause();
    currentAudio.currentTime = 0;
  }

  const playButton = document.getElementById('playExcuseBtn');
  if (playButton) {
    playButton.disabled = true; // Disable button during processing
    // Store the original HTML content of the button to restore it later
    const originalButtonHtml = playButton.innerHTML;
    playButton.innerHTML =
      '<div class="spinner spinner-small"></div> Generating Audio...'; // Show spinner inside button
  }

  try {
    const response = await fetch('/speak_excuse', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ excuse: excuse, excuse_id: excuseId }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! Status: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    const audioUrl = data.audio_url;

    if (audioUrl) {
      currentAudio = new Audio(audioUrl);
      currentAudio.play();
      currentAudio.onended = () => {
        if (playButton) {
          playButton.innerHTML = originalButtonHtml; // Restore button text
          playButton.disabled = false; // Re-enable button
        }
      };
    } else {
      console.error('Audio URL not received.');
      alert('Error: Audio URL not received. Please try again.');
    }
  } catch (error) {
    console.error('Error generating or playing audio:', error);
    alert('Error generating or playing audio. Please try again.');
  } finally {
    if (playButton) {
      // Ensure button state is restored even if an error occurs
      playButton.innerHTML =
        '<div class="spinner spinner-small"></div> Generating Audio...'; // Temporary until it's restored fully
      setTimeout(() => {
        // Use a small timeout to ensure HTML is rendered before restoring
        playButton.innerHTML = '🔊 Play Excuse'; // Restore to simple text for stability
        playButton.disabled = false;
      }, 100);
    }
  }
}

async function generateExcuse() {
  const scenario = document.getElementById('scenario').value;
  const user_role = document.getElementById('user_role').value;
  const recipient = document.getElementById('recipient').value;
  const urgency = document.getElementById('urgency').value;
  const believability = document.getElementById('believability').value;

  const excuseDiv = document.getElementById('excuse');
  const generateBtn = document.getElementById('generateExcuseBtn');

  // Show loading state for the excuse area
  excuseDiv.classList.add('generating');
  excuseDiv.innerHTML =
    '<div class="spinner"></div><p>Generating excuse...</p>';

  // Disable generate button and show spinner
  if (generateBtn) {
    generateBtn.disabled = true;
    generateBtn.innerHTML =
      '<div class="spinner spinner-small"></div> Generating...';
  }

  document.getElementById('proof_section').style.display = 'none';
  document.getElementById('proof_link').style.display = 'none';

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
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`HTTP error! status: ${response.status} - ${errorText}`);
    }

    const data = await response.json();
    console.log('Excuse response:', data);

    currentExcuseId = data.excuse_id;
    currentExcuse = data.excuse;
    currentScenario = scenario;

    // Restore excuse display and add play/download buttons with new classes
    excuseDiv.classList.remove('generating');
    excuseDiv.innerHTML = `
            <b>Excuse:</b> ${data.excuse}
            <div id="excuse-actions">
                <button id="playExcuseBtn" class="btn btn-primary">🔊 Play Excuse</button>
                <a id="downloadExcuseAudio" href="#" download="excuse_${data.excuse_id}.mp3" class="btn btn-primary">⬇ Download Audio</a>
            </div>
        `;

    // Get the audio URL from the server for the download link
    fetch('/speak_excuse', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ excuse: data.excuse, excuse_id: data.excuse_id }),
    })
      .then((audioResponse) => audioResponse.json())
      .then((audioData) => {
        if (audioData.audio_url) {
          document.getElementById('downloadExcuseAudio').href =
            audioData.audio_url;
          const filename = audioData.audio_url.split('/').pop();
          document
            .getElementById('downloadExcuseAudio')
            .setAttribute('download', filename);
        }
      })
      .catch((error) => {
        console.error('Could not fetch audio for download:', error);
        // Optionally hide the download button if audio fetch fails
        const downloadLink = document.getElementById('downloadExcuseAudio');
        if (downloadLink) downloadLink.style.display = 'none';
      });

    // Add event listener to the play button (needs to be done after HTML is injected)
    document.getElementById('playExcuseBtn').addEventListener('click', () => {
      playExcuse(data.excuse, data.excuse_id);
    });

    document.getElementById('proof_section').style.display = 'flex'; // Changed to flex for proper layout
  } catch (error) {
    excuseDiv.classList.remove('generating');
    excuseDiv.innerHTML = `Error: Failed to generate excuse. Please try again.`;
    console.error('Excuse generation error:', error);
  } finally {
    // Always re-enable generate button
    if (generateBtn) {
      generateBtn.disabled = false;
      generateBtn.innerHTML = 'Generate Excuse';
    }
  }
}

async function generateProof() {
  if (!currentExcuseId || !currentScenario) {
    document.getElementById('proof_link').style.display = 'flex'; // Changed to flex
    document.getElementById('proof_link').innerHTML =
      '<p class="loading-text">Error: No excuse generated to create proof for.</p>'; // Use loading-text style for error
    return;
  }
  const proof_type = document.getElementById('proof_type').value;
  document.getElementById('proof_link').style.display = 'flex'; // Changed to flex

  const generateProofBtn = document.getElementById('generateProofBtn');
  if (generateProofBtn) {
    generateProofBtn.disabled = true;
    generateProofBtn.innerHTML =
      '<div class="spinner spinner-small"></div> Generating...';
  }

  document.getElementById('proof_link').innerHTML =
    '<div class="spinner spinner-small"></div><p>Generating proof...</p>';

  try {
    const response = await fetch(`/generate_proof/${currentExcuseId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        excuse: currentExcuse,
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
      document.getElementById(
        'proof_link'
      ).innerHTML = `<p class="loading-text">Error: ${data.error}</p>`;
      return;
    }

    const downloadUrl = data.proof_url;
    const filename = downloadUrl.split('/').pop();

    let downloadMessage = `<p>Proof generated: <a href="${downloadUrl}" target="_blank" download="${filename}">⬇ Download ${toTitleCase(
      proof_type
    )}</a></p>`;

    // Add specific instructions for download behavior
    if (proof_type === 'doctor_note') {
      downloadMessage += `<small>If the PDF opens in your browser instead of downloading, right-click the link and choose "Save link as..." or "Download linked file".</small>`;
    } else if (proof_type === 'chat_screenshot') {
      downloadMessage += `<small>Your PNG should download automatically. If not, right-click the link and choose "Save link as...".</small>`;
    } else if (proof_type === 'location_log') {
      downloadMessage += `<small>Your JSON should download automatically. If not, right-click the link and choose "Save link as...".</small>`;
    }

    document.getElementById('proof_link').innerHTML = downloadMessage;
  } catch (error) {
    document.getElementById(
      'proof_link'
    ).innerHTML = `<p class="loading-text">Error: Failed to generate proof. Please try again.</p>`;
    console.error('Proof generation error:', error);
  } finally {
    if (generateProofBtn) {
      generateProofBtn.disabled = false;
      generateProofBtn.innerHTML = 'Generate Proof';
    }
  }
}
