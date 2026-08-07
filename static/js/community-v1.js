(function () {
  'use strict';

  var app = document.querySelector('[data-community-app]');
  if (!app) return;

  var viewportMeta = document.querySelector('meta[name="viewport"]');
  if (viewportMeta) {
    viewportMeta.setAttribute(
      'content',
      'width=device-width, initial-scale=1, viewport-fit=cover'
    );
  }

  var owner = app.dataset.owner === 'true';
  var feedList = app.querySelector('[data-feed-list]');
  var demoNote = app.querySelector('[data-community-demo-note]');
  var feedEnd = app.querySelector('[data-feed-end]');
  var loadMore = app.querySelector('[data-load-more]');
  var searchInput = app.querySelector('[data-community-search]');
  var clearSearch = app.querySelector('[data-clear-search]');
  var quickCompose = app.querySelector('.cv1-quick-compose');
  var demoQuickCompose = app.querySelector('[data-demo-quick-compose]');
  var demoComposer = app.querySelector('[data-demo-composer]');
  var demoComposerForm = app.querySelector('[data-demo-composer-form]');
  var composer = app.querySelector('[data-composer]');
  var composerForm = app.querySelector('[data-composer-form]');
  var publicConfirmation = app.querySelector('[data-public-confirmation]');
  var conversation = app.querySelector('[data-conversation]');
  var conversationBody = app.querySelector('[data-conversation-body]');
  var conversationHeaderActions = app.querySelector('[data-conversation-header-actions]');
  var replyForm = app.querySelector('[data-reply-form]');
  var catchupDialog = app.querySelector('[data-catchup-dialog]');
  var activityDialog = app.querySelector('[data-activity-dialog]');
  var publicationBanner = app.querySelector('[data-publication-banner]');
  var toast = app.querySelector('[data-community-toast]');
  var composerPlaceholder = composer ? document.createComment('community-composer-home') : null;
  if (composer) composer.parentNode.insertBefore(composerPlaceholder, composer);

  var state = {
    cursor: null,
    loading: false,
    currentPost: null,
    conversationFocusKey: null,
    selectedContribution: null,
    selectedAncestors: [],
    conversationRequest: 0,
    replyParentKey: null,
    replyDraftTargetKey: null,
    attachments: [],
    replyAttachments: [],
    editPost: null,
    sparkPrompt: null,
    searchTimer: null,
    searchRequest: 0,
    lastSearch: '',
    postCommandKey: null,
    postPayloadFingerprint: null,
    publicationConfirming: false,
    replyCommandKey: null,
    replyPayloadFingerprint: null,
    conversationReturn: null,
    conversationPushed: false,
    activityReturnFocus: null,
    catchupReturnFocus: null,
    sheetHistory: null,
    sheetHistoryClosing: false,
    demoAttachments: []
  };
  var legacyDraftKey = 'peerslate-community-owner-draft-v1';
  var draftKey = owner && app.dataset.draftNamespace
    ? legacyDraftKey + ':' + app.dataset.draftNamespace
    : null;
  var postCommandStorageKey = draftKey ? draftKey + ':pending-command' : null;
  // Approved retention decision, 2026-08-03: a device-local draft expires
  // after 30 days without an edit. Nothing is transmitted to PeerSlate, so
  // this is enforced here, on the only device that holds it.
  var DRAFT_IDLE_LIMIT_MS = 30 * 24 * 60 * 60 * 1000;

  function draftHasExpired(value) {
    if (!value || typeof value.saved_at !== 'number') return false;
    return (Date.now() - value.saved_at) > DRAFT_IDLE_LIMIT_MS;
  }
  var replyCommandStorageKey = draftKey ? draftKey + ':pending-reply-command' : null;
  var maximumReplyDepth = 8;
  if (owner) {
    try { localStorage.removeItem(legacyDraftKey); } catch (ignoreLegacyDraft) {}
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function svgPart(tag, attributes) {
    var node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    Object.keys(attributes || {}).forEach(function (name) { node.setAttribute(name, attributes[name]); });
    return node;
  }

  function cardActionIcon(kind) {
    var svg = svgPart('svg', {
      viewBox: '0 0 28 28',
      'aria-hidden': 'true',
      focusable: 'false'
    });
    if (kind === 'respond') {
      svg.classList.add('cv1-respond-symbol');
      svg.appendChild(svgPart('path', {
        d: 'M3.5 7.5h8.2a4 4 0 0 1 4 4v.4a4 4 0 0 1-4 4H8.6L5 18.8v-2.9H4.7a3.2 3.2 0 0 1-3.2-3.2v-2a3.2 3.2 0 0 1 2-3.2Z'
      }));
      svg.appendChild(svgPart('path', {
        d: 'M12.2 15.8a3.9 3.9 0 0 0 3.7 2.7h2.8l3.3 2.6v-2.8a3.2 3.2 0 0 0 2.5-3.1v-2a3.2 3.2 0 0 0-3.2-3.2h-3.1'
      }));
      svg.appendChild(svgPart('path', {
        d: 'M22.1 2.2c.3 1.45 1.2 2.35 2.65 2.65-1.45.3-2.35 1.2-2.65 2.65-.3-1.45-1.2-2.35-2.65-2.65 1.45-.3 2.35-1.2 2.65-2.65Z'
      }));
    } else {
      svg.classList.add('cv1-comment-symbol');
      svg.appendChild(svgPart('path', {
        d: 'M5.2 5.5h12.6a5.2 5.2 0 0 1 5.2 5.2v2.6a5.2 5.2 0 0 1-5.2 5.2h-6.1L6 22.8v-4.3h-.8A4.2 4.2 0 0 1 1 14.3v-4.6a4.2 4.2 0 0 1 4.2-4.2Z'
      }));
    }
    return svg;
  }

  var primaryResponseChoices = [
    {value: 'celebrate', emoji: '🎉', label: 'Celebrate'},
    {value: 'support', emoji: '❤️', label: 'Support'},
    {value: 'i_relate', emoji: '🤝', label: 'I relate'},
    {value: 'ask', emoji: '🤔', label: 'Ask'},
    {value: 'offer_help', emoji: '🙋', label: 'Offer help'}
  ];

  function primaryResponseChoice(response) {
    return primaryResponseChoices.find(function (choice) { return choice.value === response; }) || null;
  }

  function setRespondControl(control, response) {
    var selected = primaryResponseChoice(response);
    control.replaceChildren();
    if (selected) control.appendChild(el('span', 'cv1-selected-response-emoji', selected.emoji));
    else control.appendChild(cardActionIcon('respond'));
    control.setAttribute('aria-label', selected ? 'Respond: ' + selected.label : 'Respond');
    control.setAttribute('title', selected ? selected.label : 'Respond');
    control.setAttribute('aria-pressed', response ? 'true' : 'false');
  }

  function openPrimaryResponsePicker(wrapper) {
    window.clearTimeout(wrapper._communityResponseCloseTimer);
    app.querySelectorAll('[data-primary-response-control]').forEach(function (candidate) {
      if (candidate === wrapper) return;
      var otherPicker = candidate.querySelector('[data-primary-response-picker]');
      var otherTrigger = candidate.querySelector('[data-primary-response-trigger]');
      if (otherPicker) otherPicker.hidden = true;
      if (otherTrigger) otherTrigger.setAttribute('aria-expanded', 'false');
    });
    wrapper.querySelector('[data-primary-response-picker]').hidden = false;
    wrapper.querySelector('[data-primary-response-trigger]').setAttribute('aria-expanded', 'true');
  }

  function closePrimaryResponsePicker(wrapper, restoreFocus) {
    if (!wrapper) return;
    window.clearTimeout(wrapper._communityResponseCloseTimer);
    var picker = wrapper.querySelector('[data-primary-response-picker]');
    var trigger = wrapper.querySelector('[data-primary-response-trigger]');
    if (trigger && restoreFocus) trigger.focus();
    if (picker) picker.hidden = true;
    if (trigger) {
      trigger.setAttribute('aria-expanded', 'false');
    }
  }

  function schedulePrimaryResponseClose(wrapper) {
    window.clearTimeout(wrapper._communityResponseCloseTimer);
    wrapper._communityResponseCloseTimer = window.setTimeout(function () {
      if (!wrapper.matches(':hover') && !wrapper.contains(document.activeElement)) {
        closePrimaryResponsePicker(wrapper, false);
      }
    }, 180);
  }

  function primaryRespondControl(post, surface) {
    var response = post.viewer && post.viewer.response;
    var wrapper = el('div', 'cv1-response-control');
    wrapper.dataset.primaryResponseControl = '';
    var control = button('', 'respond', 'cv1-icon-action cv1-respond-trigger');
    var picker = el('div', 'cv1-response-picker');
    var pickerId = 'cv1-response-' + (surface || 'feed') + '-' + post.key;
    control.dataset.primaryResponseTrigger = '';
    control.setAttribute('aria-controls', pickerId);
    control.setAttribute('aria-expanded', 'false');
    setRespondControl(control, response);
    picker.id = pickerId;
    picker.dataset.primaryResponsePicker = '';
    picker.setAttribute('role', 'group');
    picker.setAttribute('aria-label', 'Choose a private response');
    picker.hidden = true;
    primaryResponseChoices.forEach(function (choice) {
      var option = button('', 'primary-response', 'cv1-response-choice');
      option.dataset.response = choice.value;
      option.setAttribute('aria-label', choice.label);
      option.setAttribute('aria-pressed', choice.value === response ? 'true' : 'false');
      option.appendChild(el('span', 'cv1-response-emoji', choice.emoji));
      var tooltip = el('span', 'cv1-response-tooltip', choice.label);
      tooltip.setAttribute('aria-hidden', 'true');
      option.appendChild(tooltip);
      picker.appendChild(option);
    });
    wrapper.appendChild(control);
    wrapper.appendChild(picker);
    wrapper.addEventListener('mouseenter', function () { openPrimaryResponsePicker(wrapper); });
    wrapper.addEventListener('mouseleave', function () { schedulePrimaryResponseClose(wrapper); });
    wrapper.addEventListener('focusin', function () { openPrimaryResponsePicker(wrapper); });
    wrapper.addEventListener('focusout', function () {
      window.setTimeout(function () {
        if (!wrapper.contains(document.activeElement)) schedulePrimaryResponseClose(wrapper);
      }, 0);
    });
    wrapper.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape') return;
      event.preventDefault();
      closePrimaryResponsePicker(wrapper, true);
    });
    return wrapper;
  }

  function primaryCommentIcon(kind) {
    var svg = svgPart('svg', {viewBox: '0 0 24 24', 'aria-hidden': 'true', focusable: 'false'});
    if (kind === 'voice') {
      svg.appendChild(svgPart('rect', {x: '9', y: '3', width: '6', height: '11', rx: '3'}));
      svg.appendChild(svgPart('path', {d: 'M6.5 11.5a5.5 5.5 0 0 0 11 0M12 17v4M8.5 21h7'}));
    } else {
      svg.appendChild(svgPart('path', {d: 'm5 11 7-7 7 7M12 4v16'}));
    }
    return svg;
  }

  function primaryCommentStorageKey(postKey, kind) {
    return draftKey ? draftKey + ':comment-' + kind + ':' + postKey : null;
  }

  var communityVoiceRegistry = {active: null, controllers: [], nextControllerId: 0};
  var composerVoiceController = null;
  var replyVoiceController = null;
  var demoComposerVoiceController = null;

  function utf16Length(value) {
    return String(value || '').length;
  }

  function voiceElapsedLabel(startedAt) {
    var seconds = Math.min(180, Math.max(0, Math.floor((Date.now() - startedAt) / 1000)));
    return Math.floor(seconds / 60) + ':' + ('0' + (seconds % 60)).slice(-2);
  }

  function CommunityVoiceController(options) {
    this.form = options.form;
    this.input = options.input;
    this.trigger = options.trigger;
    this.mirrors = options.mirrors || [];
    this.context = options.context;
    this.maxLength = options.maxLength;
    this.noun = options.noun;
    this.resize = options.resize || function () {};
    this.lifetime = options.lifetime || 'page';
    this.localOnly = Boolean(options.localOnly);
    this.id = 'cv1-voice-controller-' + (++communityVoiceRegistry.nextControllerId);
    this.state = 'ready';
    this.stream = null;
    this.recorder = null;
    this.chunks = [];
    this.blob = null;
    this.startedAt = null;
    this.durationSeconds = null;
    this.stopTimer = null;
    this.elapsedTimer = null;
    this.elapsedNode = null;
    this.abortController = null;
    this.cancelled = false;
    this.panel = el('section', 'cv1-comment-voice-panel');
    this.panel.hidden = true;
    this.panel.dataset.voiceState = 'ready';
    this.panel.setAttribute('aria-label', 'Voice ' + this.noun + ' review');
    this.status = el('p', 'cv1-comment-voice-status');
    this.status.setAttribute('role', 'status');
    this.status.setAttribute('aria-live', 'polite');
    (options.panelHost || this.form).appendChild(this.panel);
    this.form._communityVoiceController = this;
    communityVoiceRegistry.controllers.push(this);
    this.render();
  }

  CommunityVoiceController.prototype.isActive = function () {
    return this.state === 'permission' || this.state === 'recording' || this.state === 'processing';
  };

  CommunityVoiceController.prototype.claim = function () {
    if (communityVoiceRegistry.active && communityVoiceRegistry.active !== this) {
      showToast('Finish or discard the other Voice comment before starting another recording.', true);
      return false;
    }
    communityVoiceRegistry.active = this;
    return true;
  };

  CommunityVoiceController.prototype.release = function () {
    if (communityVoiceRegistry.active === this) communityVoiceRegistry.active = null;
  };

  CommunityVoiceController.prototype.stopTracks = function () {
    if (!this.stream || !this.stream.getTracks) return;
    this.stream.getTracks().forEach(function (track) { track.stop(); });
    this.stream = null;
  };

  CommunityVoiceController.prototype.clearAudio = function () {
    if (this.abortController) this.abortController.abort();
    this.abortController = null;
    if (this.stopTimer) window.clearTimeout(this.stopTimer);
    this.stopTimer = null;
    if (this.elapsedTimer) window.clearInterval(this.elapsedTimer);
    this.elapsedTimer = null;
    this.elapsedNode = null;
    this.stopTracks();
    this.recorder = null;
    this.chunks = [];
    this.blob = null;
    this.startedAt = null;
    this.durationSeconds = null;
    this.release();
  };

  CommunityVoiceController.prototype.focusTrigger = function () {
    var control = this.trigger;
    window.setTimeout(function () { if (control && control.isConnected) control.focus(); }, 0);
  };

  CommunityVoiceController.prototype.setState = function (state, message) {
    this.state = state;
    this.status.textContent = message || '';
    this.panel.dataset.voiceState = state;
    this.panel.hidden = state === 'ready' || state === 'ready-to-send';
    [this.trigger].concat(this.mirrors).forEach(function (trigger) {
      if (!trigger) return;
      trigger.setAttribute('aria-pressed', state === 'recording' ? 'true' : 'false');
      trigger.setAttribute('aria-label', state === 'recording' ? 'Recording Voice ' + this.noun : 'Start Voice ' + this.noun + ' recording');
    }, this);
    this.render();
  };

  CommunityVoiceController.prototype.action = function (label, handler, extraClass) {
    var control = button(label, '', 'cv1-voice-control' + (extraClass ? ' ' + extraClass : ''));
    control.addEventListener('click', handler);
    return control;
  };

  CommunityVoiceController.prototype.render = function () {
    var self = this;
    this.panel.replaceChildren();
    if (this.state === 'ready' || this.state === 'ready-to-send') return;
    this.panel.appendChild(this.status);
    if (this.state === 'permission') {
      this.panel.appendChild(this.action('Cancel', function () { self.discard(true); }, 'cv1-secondary'));
      return;
    }
    if (this.state === 'recording') {
      var waveform = el('span', 'cv1-comment-voice-waveform');
      waveform.setAttribute('aria-hidden', 'true');
      waveform.appendChild(el('i'));
      waveform.appendChild(el('i'));
      waveform.appendChild(el('i'));
      this.panel.appendChild(waveform);
      this.elapsedNode = el('span', 'cv1-comment-voice-elapsed', voiceElapsedLabel(this.startedAt));
      this.elapsedNode.setAttribute('aria-hidden', 'true');
      this.panel.appendChild(this.elapsedNode);
      this.panel.appendChild(this.action('Stop', function () { self.stopRecording(); }, 'cv1-primary'));
      this.panel.appendChild(this.action('Cancel', function () { self.discard(true); }, 'cv1-secondary'));
      return;
    }
    if (this.state === 'processing') {
      var processing = el('span', 'cv1-comment-voice-processing');
      processing.setAttribute('aria-hidden', 'true');
      this.panel.appendChild(processing);
      this.panel.appendChild(this.action('Cancel', function () { self.discard(true); }, 'cv1-secondary'));
      return;
    }
    if (this.state === 'preview') {
      var label = el('label', 'cv1-comment-voice-review-label', 'Review transcript before using it');
      var proposal = el('textarea', 'cv1-comment-voice-proposal');
      proposal.rows = 3;
      proposal.maxLength = this.maxLength;
      proposal.value = this.proposal || '';
      proposal.setAttribute('aria-label', 'Editable Voice transcript proposal');
      proposal.addEventListener('input', function () { self.proposal = proposal.value; });
      label.htmlFor = this.id + '-proposal';
      proposal.id = label.htmlFor;
      this.panel.appendChild(label);
      this.panel.appendChild(proposal);
      this.panel.appendChild(this.action('Use transcript', function () { self.useTranscript(); }, 'cv1-primary'));
      this.panel.appendChild(this.action('Discard', function () { self.discard(true); }, 'cv1-secondary'));
      return;
    }
    if (this.state === 'local-review') {
      this.panel.appendChild(el('span', 'cv1-comment-voice-elapsed', Math.max(1, Math.round(this.durationSeconds || 0)) + ' sec'));
      this.panel.appendChild(this.action('Record again', function () {
        self.discard(false);
        self.start();
      }, 'cv1-primary'));
      this.panel.appendChild(this.action('Discard', function () { self.discard(true); }, 'cv1-secondary'));
      return;
    }
    if (this.state === 'failure') {
      if (this.blob) {
        if (this.retryable) this.panel.appendChild(this.action('Retry', function () { self.transcribe(); }, 'cv1-primary'));
        this.panel.appendChild(this.action('Discard', function () { self.discard(true); }, 'cv1-secondary'));
      } else {
        this.panel.appendChild(this.action('Try again', function () { self.start(); }, 'cv1-primary'));
        this.panel.appendChild(this.action('Not now', function () { self.discard(true); }, 'cv1-secondary'));
      }
    }
  };

  CommunityVoiceController.prototype.start = function () {
    var self = this;
    if (this.isActive()) return;
    if (this.state === 'preview' || this.state === 'local-review' || this.state === 'failure') this.discard(false);
    if (!this.claim()) return;
    this.cancelled = false;
    this.durationSeconds = null;
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
      this.release();
      this.setState('failure', 'Voice recording is unavailable on this device. You can keep typing.');
      this.focusTrigger();
      return;
    }
    this.setState('permission', 'Requesting microphone permission. You can keep typing.');
    navigator.mediaDevices.getUserMedia({audio: true}).then(function (stream) {
      if (self.cancelled || self.state !== 'permission') {
        stream.getTracks().forEach(function (track) { track.stop(); });
        return;
      }
      self.stream = stream;
      try {
        self.recorder = new MediaRecorder(stream);
      } catch (error) {
        self.clearAudio();
        self.setState('failure', 'Voice recording is unavailable on this device. You can keep typing.');
        self.focusTrigger();
        return;
      }
      self.chunks = [];
      self.recorder.addEventListener('dataavailable', function (event) {
        if (event.data && event.data.size) self.chunks.push(event.data);
      });
      self.recorder.addEventListener('stop', function () {
        if (self.elapsedTimer) window.clearInterval(self.elapsedTimer);
        self.elapsedTimer = null;
        self.elapsedNode = null;
        self.stopTracks();
        if (self.cancelled) return;
        if (!self.durationSeconds && self.startedAt) {
          self.durationSeconds = Math.min(180, Math.max(.01, (Date.now() - self.startedAt) / 1000));
        }
        var type = self.recorder && self.recorder.mimeType || 'audio/webm';
        self.blob = new Blob(self.chunks, {type: type});
        self.chunks = [];
        if (!self.blob.size) {
          self.setState('failure', 'No recording was captured. You can keep typing or record again.');
          self.release();
          self.focusTrigger();
          return;
        }
        if (self.localOnly) {
          self.release();
          self.setState('local-review', 'Recording captured locally. It was not uploaded or transcribed and will disappear when this page closes.');
          return;
        }
        self.transcribe();
      });
      self.startedAt = Date.now();
      try {
        self.recorder.start();
      } catch (error) {
        self.clearAudio();
        self.setState('failure', 'Voice recording is unavailable on this device. You can keep typing.');
        self.focusTrigger();
        return;
      }
      self.setState('recording', self.localOnly
        ? 'Recording locally. Stop when you are ready; this audio will not leave your browser.'
        : 'Recording. Stop when you are ready to review the transcript.');
      self.elapsedTimer = window.setInterval(function () {
        if (self.elapsedNode) self.elapsedNode.textContent = voiceElapsedLabel(self.startedAt);
      }, 1000);
      self.stopTimer = window.setTimeout(function () {
        if (self.state === 'recording') self.stopRecording(true);
      }, 180000);
    }).catch(function () {
      if (self.cancelled || self.state !== 'permission') return;
      self.release();
      self.setState('failure', 'Microphone permission was not granted. You can keep typing.');
      self.focusTrigger();
    });
  };

  CommunityVoiceController.prototype.stopRecording = function (reachedLimit) {
    if (this.state !== 'recording' || !this.recorder) return;
    if (this.stopTimer) window.clearTimeout(this.stopTimer);
    this.stopTimer = null;
    if (this.elapsedTimer) window.clearInterval(this.elapsedTimer);
    this.elapsedTimer = null;
    this.elapsedNode = null;
    this.durationSeconds = Math.min(180, Math.max(.01, (Date.now() - this.startedAt) / 1000));
    this.setState('processing', this.localOnly
      ? (reachedLimit ? 'The three-minute recording limit was reached. Finishing the local recording.' : 'Finishing the local recording.')
      : (reachedLimit
        ? 'The three-minute recording limit was reached. Transcribing your recording. You can keep typing.'
        : 'Transcribing your recording. You can keep typing.'));
    this.recorder.stop();
  };

  CommunityVoiceController.prototype.transcribe = function () {
    var self = this;
    if (!this.blob || !this.claim()) return;
    this.setState('processing', 'Transcribing your recording. You can keep typing.');
    var data = new FormData();
    data.append('audio', this.blob, 'voice-' + this.context + '.webm');
    data.append('duration_seconds', String(this.durationSeconds || .01));
    data.append('composer_context', this.context);
    this.abortController = new AbortController();
    api('/api/v1/community/voice/transcriptions', {
      method: 'POST', body: data, signal: this.abortController.signal
    }).then(function (payload) {
      self.abortController = null;
      self.release();
      self.retryable = true;
      self.proposal = payload.proposal && payload.proposal.text || '';
      if (!self.proposal) throw new Error('No reviewable speech was detected.');
      self.setState('preview', 'Review the transcript. It will not be inserted or sent until you choose Use transcript.');
      var proposal = self.panel.querySelector('.cv1-comment-voice-proposal');
      if (proposal) proposal.focus();
    }).catch(function (error) {
      if (error && error.name === 'AbortError') return;
      self.abortController = null;
      self.release();
      self.retryable = !error || error.retryable !== false;
      self.setState('failure', (error && error.message) || 'Voice transcription is unavailable. You can keep typing.');
      self.focusTrigger();
    });
  };

  CommunityVoiceController.prototype.useTranscript = function () {
    var proposal = String(this.proposal || '');
    var start = this.input.selectionStart || 0;
    var combined = this.input.value.slice(0, start) + proposal + this.input.value.slice(start);
    if (!proposal.trim() || utf16Length(combined) > this.maxLength) {
      this.setState('preview', 'The transcript and typed ' + this.noun + ' are too long together. Edit either text before using it.');
      return;
    }
    this.input.value = combined;
    this.input.setSelectionRange(start + proposal.length, start + proposal.length);
    this.clearAudio();
    this.proposal = '';
    this.setState('ready-to-send');
    this.resize();
    this.input.dispatchEvent(new Event('input', {bubbles: true}));
    this.input.focus();
  };

  CommunityVoiceController.prototype.discard = function (restoreFocus) {
    this.cancelled = true;
    if (this.recorder && this.recorder.state !== 'inactive') this.recorder.stop();
    this.clearAudio();
    this.proposal = '';
    this.setState('ready');
    if (restoreFocus) this.focusTrigger();
  };

  CommunityVoiceController.prototype.dispose = function () {
    this.discard(false);
    if (this.form._communityVoiceController === this) this.form._communityVoiceController = null;
    this.panel.remove();
    communityVoiceRegistry.controllers = communityVoiceRegistry.controllers.filter(function (controller) { return controller !== this; }, this);
  };

  CommunityVoiceController.prototype.hasUnresolvedVoice = function () {
    return this.isActive() || this.state === 'preview' || Boolean(this.blob);
  };

  function disposeCommunityVoiceControllers(lifetime) {
    communityVoiceRegistry.controllers.slice().forEach(function (controller) {
      if (!lifetime || controller.lifetime === lifetime) controller.dispose();
    });
  }

  function resizePrimaryComment(form) {
    var input = formField(form, 'body');
    var submit = form.querySelector('[type="submit"]');
    if (!input) return;
    input.style.height = 'auto';
    var nextHeight = Math.max(20, Math.min(input.scrollHeight, 112));
    input.style.height = nextHeight + 'px';
    input.style.overflowY = input.scrollHeight > 112 ? 'auto' : 'hidden';
    if (submit) submit.disabled = form.hasAttribute('data-submitting') || !input.value.trim();
  }

  function savePrimaryCommentDraft(form, postKey) {
    var key = primaryCommentStorageKey(postKey, 'draft');
    if (!key) return;
    var value = formField(form, 'body').value;
    try {
      if (value) {
        localStorage.setItem(key, JSON.stringify({ body: value, saved_at: Date.now() }));
      } else {
        localStorage.removeItem(key);
      }
    } catch (ignoreCommentDraft) {}
  }

  function readPrimaryCommentDraft(postKey) {
    var key = primaryCommentStorageKey(postKey, 'draft');
    if (!key) return '';
    try {
      var raw = localStorage.getItem(key);
      if (!raw) return '';
      // Drafts saved before the expiry envelope existed are plain strings.
      // Treat them as undated and let them expire on their next save rather
      // than discarding someone's unsent words on upgrade.
      if (raw.charAt(0) !== '{') return raw;
      var value = JSON.parse(raw);
      if (draftHasExpired(value)) {
        localStorage.removeItem(key);
        return '';
      }
      return typeof value.body === 'string' ? value.body : '';
    } catch (ignoreCommentDraftRead) {
      return '';
    }
  }

  function primaryCommentCommandKey(form, postKey, payload) {
    var fingerprint = String(postKey) + '|' + JSON.stringify(payload);
    var signature = payloadSignature(fingerprint);
    var storageKey = primaryCommentStorageKey(postKey, 'command');
    if (storageKey && !form._communityCommentCommandKey) {
      try {
        var pending = JSON.parse(localStorage.getItem(storageKey) || '{}');
        if (pending.signature === signature && typeof pending.key === 'string') {
          form._communityCommentCommandKey = pending.key;
          form._communityCommentFingerprint = fingerprint;
        } else if (pending.key) {
          localStorage.removeItem(storageKey);
        }
      } catch (ignorePendingComment) {
        try { localStorage.removeItem(storageKey); } catch (ignoreInvalidComment) {}
      }
    }
    if (form._communityCommentCommandKey && form._communityCommentFingerprint !== fingerprint) {
      form._communityCommentCommandKey = null;
      form._communityCommentFingerprint = null;
      if (storageKey) {
        try { localStorage.removeItem(storageKey); } catch (ignoreChangedComment) {}
      }
    }
    if (!form._communityCommentCommandKey) {
      form._communityCommentCommandKey = uuid();
      form._communityCommentFingerprint = fingerprint;
    }
    if (storageKey) {
      try {
        localStorage.setItem(storageKey, JSON.stringify({key: form._communityCommentCommandKey, signature: signature}));
      } catch (ignoreCommentCommandWrite) {}
    }
    return form._communityCommentCommandKey;
  }

  function updatePrimaryCommentCount(card, post) {
    var count = Number(post.contribution_count || 0);
    var control = card.querySelector('.cv1-comment-trigger');
    var copy = primaryPostCopy(post.body);
    if (!control) return;
    control.querySelector('.cv1-action-count').textContent = count;
    control.setAttribute(
      'aria-label',
      'Open conversation: ' + copy.title + ' · ' + count + (count === 1 ? ' comment' : ' comments')
    );
  }

  function sendPrimaryComment(event, post) {
    event.preventDefault();
    var form = event.currentTarget;
    var input = formField(form, 'body');
    var body = input.value.trim();
    if (!body || form.hasAttribute('data-submitting')) return;
    var payload = {body: body, parent_key: null, attachment_keys: []};
    form.dataset.submitting = '';
    resizePrimaryComment(form);
    api(
      '/api/v1/community/posts/' + encodeURIComponent(post.key) + '/contributions',
      jsonOptions('POST', payload, primaryCommentCommandKey(form, post.key, payload))
    ).then(function () {
      [primaryCommentStorageKey(post.key, 'draft'), primaryCommentStorageKey(post.key, 'command')].forEach(function (key) {
        if (!key) return;
        try { localStorage.removeItem(key); } catch (ignoreCommentCleanup) {}
      });
      form._communityCommentCommandKey = null;
      form._communityCommentFingerprint = null;
      form.reset();
      if (form._communityVoiceController) form._communityVoiceController.discard(false);
      post.contribution_count = Number(post.contribution_count || 0) + 1;
      updatePrimaryCommentCount(form.closest('[data-primary-feed-card]'), post);
      showToast('Comment published.');
    }).catch(function (error) {
      var retryHint = error.retryable === false ? '' : ' You can try again without creating a duplicate.';
      showToast(error.message + retryHint, true);
    }).finally(function () {
      form.removeAttribute('data-submitting');
      resizePrimaryComment(form);
    });
  }

  function primaryCommentComposer(post) {
    var form = el('form', 'cv1-primary-comment');
    var field = el('div', 'cv1-primary-comment-field');
    var input = el('textarea', 'cv1-primary-comment-input');
    var label = el('label', 'cv1-visually-hidden', 'Write a comment');
    var voice = button('', 'voice-comment', 'cv1-primary-comment-voice');
    var demo = Boolean(post.demo);
    var submit = demo ? null : el('button', 'cv1-primary-comment-send');
    var inputId = 'cv1-primary-comment-' + post.key;
    var draftStorageKey = demo ? null : primaryCommentStorageKey(post.key, 'draft');

    form.dataset.primaryComment = '';
    form.dataset.postKey = post.key;
    if (demo) form.classList.add('cv1-primary-comment--demo');
    label.htmlFor = inputId;
    input.id = inputId;
    input.name = 'body';
    input.rows = 1;
    input.maxLength = 2000;
    input.required = true;
    input.placeholder = demo ? 'Try writing a comment…' : 'Write a comment…';
    input.setAttribute('aria-label', demo ? 'Try writing a demo comment' : 'Write a comment');
    if (draftStorageKey) {
      input.value = readPrimaryCommentDraft(post.key);
    }

    voice.setAttribute('aria-label', 'Start Voice comment recording');
    voice.setAttribute('aria-pressed', 'false');
    voice.setAttribute('title', 'Record a private Voice comment');
    voice.appendChild(primaryCommentIcon('voice'));
    if (submit) {
      submit.type = 'submit';
      submit.disabled = true;
      submit.setAttribute('aria-label', 'Publish comment');
      submit.setAttribute('title', 'Publish comment');
      submit.appendChild(primaryCommentIcon('send'));
    }

    field.appendChild(input);
    field.appendChild(voice);
    if (submit) field.appendChild(submit);
    form.appendChild(label);
    form.appendChild(field);
    var voiceController = new CommunityVoiceController({
      form: form,
      input: input,
      trigger: voice,
      context: 'contribution',
      maxLength: 2000,
      noun: 'comment',
      resize: function () { resizePrimaryComment(form); },
      lifetime: 'feed',
      localOnly: demo && !owner
    });
    if (demo) form.appendChild(el('span', 'cv1-demo-comment-note', 'Demo only · nothing will be sent.'));
    input.addEventListener('input', function () {
      resizePrimaryComment(form);
      if (!demo) savePrimaryCommentDraft(form, post.key);
    });
    input.addEventListener('keydown', function (event) {
      if (!demo && (event.metaKey || event.ctrlKey) && event.key === 'Enter' && input.value.trim()) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
    voice.addEventListener('click', function () { voiceController.start(); });
    form.addEventListener('submit', function (event) {
      if (demo) event.preventDefault();
      else sendPrimaryComment(event, post);
    });
    window.requestAnimationFrame(function () { resizePrimaryComment(form); });
    return form;
  }

  function terminalSymbol(kind) {
    var holder = el('span', 'cv1-empty-symbol');
    var svg = svgPart('svg', {viewBox: '0 0 64 64', 'aria-hidden': 'true'});
    if (kind === 'search') {
      svg.appendChild(svgPart('circle', {cx: '27', cy: '27', r: '15'}));
      svg.appendChild(svgPart('path', {d: 'M38 38 52 52'}));
    } else if (kind === 'lock') {
      svg.appendChild(svgPart('rect', {x: '16', y: '28', width: '32', height: '25', rx: '4'}));
      svg.appendChild(svgPart('path', {d: 'M23 28v-7a9 9 0 0 1 18 0v7'}));
    } else if (kind === 'empty') {
      svg.appendChild(svgPart('path', {d: 'M23 47h18l-2 9H25l-2-9Z'}));
      svg.appendChild(svgPart('path', {d: 'M32 47V24M32 31c-8 0-13-5-13-12 8 0 13 5 13 12Zm0 5c8 0 13-5 13-12-8 0-13 5-13 12Z'}));
    } else {
      svg.appendChild(svgPart('path', {d: 'M18 42c10 0 21-11 21-21-10 0-21 11-21 21Zm0 0 8 8M37 18l9-5M41 24l10 1'}));
      svg.appendChild(svgPart('path', {d: 'M12 53h28'}));
    }
    holder.appendChild(svg);
    return holder;
  }

  function button(label, action, className) {
    var node = el('button', className || '', label);
    node.type = 'button';
    if (action) node.dataset.action = action;
    return node;
  }

  function showToast(message, error) {
    toast.textContent = message;
    toast.style.borderColor = error ? '#efb4b4' : '';
    toast.style.background = error ? '#fff0ef' : '';
    toast.style.color = error ? '#8d1d1d' : '';
    toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(function () { toast.hidden = true; }, 4200);
  }

  function uuid() {
    if (window.crypto && window.crypto.randomUUID) return window.crypto.randomUUID();
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 3 | 8)).toString(16);
    });
  }

  function formField(form, name) {
    return form && form.elements ? form.elements.namedItem(name) : null;
  }

  function api(url, options) {
    options = options || {};
    options.headers = options.headers || {};
    if (options.method && options.method !== 'GET') {
      options.headers['X-PeerSlate-Request'] = 'same-origin';
    }
    return fetch(url, options).then(function (response) {
      var type = response.headers.get('content-type') || '';
      return (type.indexOf('application/json') >= 0 ? response.json() : Promise.resolve({}))
        .then(function (payload) {
          if (!response.ok) {
            var failure = new Error(payload.message || 'Community could not complete that request.');
            failure.status = response.status;
            failure.retryable = payload.retryable !== false;
            throw failure;
          }
          return payload;
        });
    });
  }

  function jsonOptions(method, payload, idempotency) {
    var headers = {'Content-Type': 'application/json'};
    if (idempotency) headers['Idempotency-Key'] = idempotency;
    return {method: method, headers: headers, body: JSON.stringify(payload || {})};
  }

  function relativeTime(value) {
    var date = new Date(value);
    if (!value || Number.isNaN(date.getTime())) return '';
    var seconds = Math.max(0, Math.round((Date.now() - date.getTime()) / 1000));
    if (seconds < 60) return 'just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    if (seconds < 604800) return Math.floor(seconds / 86400) + 'd ago';
    return date.toLocaleDateString(undefined, {month: 'short', day: 'numeric'});
  }

  function attachmentNode(item, activation) {
    var opensConversation = Boolean(activation && item.preview_url);
    var href = opensConversation ? activation.permalink : (item.preview_url || item.download_url);
    var link = href ? el('a', 'cv1-attachment') : el('span', 'cv1-attachment cv1-attachment--demo');
    if (href) {
      link.href = href;
      link.target = item.preview_url && !opensConversation ? '_blank' : '';
      link.rel = 'noopener';
    }
    if (opensConversation) {
      link.dataset.action = 'conversation';
      link.dataset.postKey = activation.postKey;
      link.setAttribute('aria-label', 'Open conversation: ' + activation.title);
    }
    if (item.preview_url) {
      link.classList.add('cv1-attachment--image');
      var image = el('img');
      image.src = item.preview_url;
      image.alt = item.display_name;
      image.loading = 'lazy';
      link.appendChild(image);
    } else {
      link.appendChild(el('span', '', '▱'));
      var copy = el('span', 'cv1-attachment-name');
      copy.appendChild(el('strong', '', item.display_name));
      copy.appendChild(document.createElement('br'));
      var fileKind = item.content_type === 'application/pdf'
        ? 'PDF document'
        : (item.content_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          ? 'Excel spreadsheet'
          : 'File');
      copy.appendChild(el('small', '', item.demo ? fileKind + ' · illustrative file' : fileKind + ' · ' + Math.max(1, Math.round(item.byte_length / 1024)) + ' KB'));
      link.appendChild(copy);
    }
    return link;
  }

  function avatar(author) {
    author = author || {display_name: 'PeerSlate member'};
    var node = el('span', 'cv1-avatar', (author.display_name || 'P').slice(0, 1));
    if (author.avatar_url) {
      node.textContent = '';
      var image = el('img');
      image.src = author.avatar_url;
      image.alt = '';
      image.loading = 'lazy';
      node.appendChild(image);
    }
    return node;
  }

  function motionBehavior() {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth';
  }

  function motionDelay() {
    return motionBehavior() === 'auto' ? 0 : 350;
  }

  function attachmentsNode(items, activation) {
    var files = el('div', 'cv1-attachments');
    var images = (items || []).filter(function (item) { return Boolean(item.preview_url); });
    var documents = (items || []).filter(function (item) { return !item.preview_url; });
    if (images.length > 1) {
      var gallery = el('div', 'cv1-image-gallery cv1-image-gallery--' + Math.min(4, images.length));
      gallery.setAttribute('role', 'group');
      gallery.setAttribute('aria-label', images.length + ' attached images');
      images.forEach(function (item) { gallery.appendChild(attachmentNode(item, activation)); });
      files.appendChild(gallery);
    } else {
      images.forEach(function (item) { files.appendChild(attachmentNode(item, activation)); });
    }
    documents.forEach(function (item) { files.appendChild(attachmentNode(item)); });
    return files;
  }

  function compactAttachmentCue(item) {
    var attachments = item.attachments || [];
    if (!attachments.length) return null;
    var first = attachments[0];
    var cue = el('span', 'cv1-shelf-attachment');
    if (first.preview_url) {
      var thumbnail = el('img');
      thumbnail.src = first.preview_url;
      thumbnail.alt = '';
      thumbnail.loading = 'lazy';
      cue.appendChild(thumbnail);
    } else {
      var fileLabel = 'FILE';
      if (first.content_type === 'application/pdf') fileLabel = 'PDF';
      if (first.content_type === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet') fileLabel = 'XLSX';
      var fileIcon = el('span', 'cv1-shelf-attachment__icon', fileLabel);
      fileIcon.setAttribute('aria-hidden', 'true');
      cue.appendChild(fileIcon);
    }
    cue.appendChild(el('span', 'cv1-shelf-attachment__name', first.display_name));
    if (attachments.length > 1) cue.appendChild(el('span', 'cv1-shelf-attachment__more', '+' + (attachments.length - 1)));
    return cue;
  }

  function appendShelfItems(shelf, items) {
    var track = shelf.querySelector('[data-conversation-shelf-track]');
    var seen = {};
    track.querySelectorAll('[data-contribution-key]').forEach(function (card) {
      seen[card.dataset.contributionKey] = true;
    });
    (items || []).forEach(function (item) {
      if (seen[item.key]) return;
      seen[item.key] = true;
      var card = button('', 'select-contribution');
      card.dataset.conversationShelfCard = '';
      card.dataset.postKey = shelf._communityShelf.postKey;
      card.dataset.contributionKey = item.key;
      card.dataset.contributionKind = item.kind || 'comment';
      card.setAttribute('aria-label', 'Open reply from ' + item.author.display_name);
      card.appendChild(el('strong', '', item.author.display_name));
      card.appendChild(el('p', '', item.body));
      var attachment = compactAttachmentCue(item);
      if (attachment) card.appendChild(attachment);
      var context = relativeTime(item.created_at_utc);
      if (item.child_reply_count) context += ' · ' + item.child_reply_count + (item.child_reply_count === 1 ? ' reply' : ' replies');
      card.appendChild(el('small', '', context));
      var listItem = el('li');
      var position = track.querySelectorAll(':scope > li').length + 1;
      listItem.setAttribute('aria-posinset', String(position));
      listItem.setAttribute('aria-setsize', String(Math.max(position, shelf._communityShelf.total)));
      listItem.appendChild(card);
      track.appendChild(listItem);
    });
  }

  function updateShelfControls(shelf) {
    var track = shelf.querySelector('[data-conversation-shelf-track]');
    var previous = shelf.querySelector('[data-shelf-previous]');
    var next = shelf.querySelector('[data-shelf-next]');
    var atStart = track.scrollLeft <= 2;
    var atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
    previous.hidden = atStart;
    next.hidden = atEnd && !shelf._communityShelf.nextCursor;
    next.disabled = shelf._communityShelf.loading;
  }

  function advanceShelf(shelf) {
    var track = shelf.querySelector('[data-conversation-shelf-track]');
    var atEnd = track.scrollLeft + track.clientWidth >= track.scrollWidth - 4;
    if (!atEnd || !shelf._communityShelf.nextCursor) {
      track.scrollBy({left: Math.max(180, track.clientWidth * 0.75), behavior: motionBehavior()});
      window.setTimeout(function () { updateShelfControls(shelf); }, motionDelay());
      return;
    }
    if (shelf._communityShelf.loading) return;
    shelf._communityShelf.loading = true;
    updateShelfControls(shelf);
    api('/api/v1/community/posts/' + encodeURIComponent(shelf._communityShelf.postKey) + '/shelf?cursor=' + encodeURIComponent(shelf._communityShelf.nextCursor))
      .then(function (payload) {
        appendShelfItems(shelf, payload.items);
        shelf._communityShelf.nextCursor = payload.next_cursor;
        window.requestAnimationFrame(function () {
          track.scrollBy({left: Math.max(180, track.clientWidth * 0.75), behavior: motionBehavior()});
          updateShelfControls(shelf);
        });
      }).catch(function (error) {
        showToast(error.message, true);
      }).finally(function () {
        shelf._communityShelf.loading = false;
        updateShelfControls(shelf);
      });
  }

  function renderConversationShelf(post) {
    if (!post.preview_contributions || !post.preview_contributions.length) return null;
    var shelf = el('section');
    shelf.dataset.conversationShelf = '';
    shelf.setAttribute('aria-label', 'Replies and updates');
    shelf._communityShelf = {
      postKey: post.key,
      nextCursor: post.next_shelf_cursor || null,
      loading: false,
      total: post.contribution_count
    };
    var head = el('div', 'cv1-conversation-shelf__head');
    var shelfTitle = el('span', 'cv1-conversation-shelf__title');
    shelfTitle.appendChild(el('strong', '', 'Replies & updates'));
    shelfTitle.appendChild(el('span', 'cv1-conversation-shelf__count', post.contribution_count + ' total'));
    head.appendChild(shelfTitle);
    var viewAll = button('', 'conversation');
    viewAll.appendChild(document.createTextNode('View all'));
    viewAll.setAttribute('aria-label', 'View all Replies & Updates');
    viewAll.dataset.postKey = post.key;
    head.appendChild(viewAll);
    shelf.appendChild(head);
    var track = el('ul');
    track.dataset.conversationShelfTrack = '';
    track.tabIndex = 0;
    shelf.appendChild(track);
    appendShelfItems(shelf, post.preview_contributions);
    var previous = button('‹', 'shelf-previous');
    previous.dataset.shelfPrevious = '';
    previous.setAttribute('aria-label', 'Previous replies and updates');
    previous.hidden = true;
    var next = button('›', 'shelf-next');
    next.dataset.shelfNext = '';
    next.setAttribute('aria-label', 'More replies and updates');
    shelf.appendChild(previous);
    shelf.appendChild(next);
    track.addEventListener('scroll', function () { updateShelfControls(shelf); }, {passive: true});
    window.requestAnimationFrame(function () { updateShelfControls(shelf); });
    return shelf;
  }

  function postOwnerControls(post, surface) {
    var ownerControls = el('div', 'cv1-card-owner-controls');
    var menuButton = button('', 'menu', 'cv1-card-menu');
    menuButton.appendChild(el('span', 'cv1-overflow-dots', '•••'));
    menuButton.setAttribute('aria-label', 'Post actions');
    menuButton.setAttribute('aria-haspopup', 'menu');
    menuButton.setAttribute('aria-expanded', 'false');
    ownerControls.appendChild(menuButton);
    var menu = el('div', 'cv1-card-owner-actions');
    menu.hidden = true;
    menu.setAttribute('role', 'menu');
    menu.id = 'cv1-post-menu-' + surface + '-' + post.key;
    menuButton.setAttribute('aria-controls', menu.id);
    var edit = button('Edit post', 'edit-post');
    edit.setAttribute('role', 'menuitem');
    menu.appendChild(edit);
    var copyLink = button('Copy link', 'copy-link');
    copyLink.setAttribute('role', 'menuitem');
    copyLink.dataset.permalink = post.permalink;
    menu.appendChild(copyLink);
    var remove = button('Delete post', 'delete-post', 'cv1-delete');
    remove.setAttribute('role', 'menuitem');
    menu.appendChild(remove);
    ownerControls.appendChild(menu);
    return ownerControls;
  }

  function primaryPostCopy(body) {
    var normalized = String(body || '').trim();
    var paragraphs = normalized.split(/\n\s*\n/).map(function (part) { return part.trim(); }).filter(Boolean);
    var lead = paragraphs.shift() || 'Community post';
    var title = lead;
    var remainder = '';
    var sentence = lead.match(/^(.{1,140}?[.!?])(?:\s+)([\s\S]+)$/);
    if (sentence) {
      title = sentence[1];
      remainder = sentence[2];
    } else {
      var leadCharacters = Array.from(lead);
      if (leadCharacters.length > 140) {
        var boundary = 140;
        for (var index = 139; index >= 60; index -= 1) {
          if (/\s/.test(leadCharacters[index])) {
            boundary = index;
            break;
          }
        }
        title = leadCharacters.slice(0, boundary).join('').trim();
        remainder = leadCharacters.slice(boundary).join('').trim();
      }
    }
    if (remainder) paragraphs.unshift(remainder);
    return {title: title, supporting: paragraphs.join('\n\n')};
  }

  function conversationPostControls(post) {
    var actions = el('div', 'cv1-card-actions cv1-card-actions--primary cv1-conversation-post-actions');
    var commentSummary = el('span', 'cv1-conversation-comment-summary');
    commentSummary.setAttribute('aria-label', post.contribution_count + (post.contribution_count === 1 ? ' comment' : ' comments'));
    commentSummary.appendChild(cardActionIcon('comment'));
    commentSummary.appendChild(el('span', 'cv1-action-count', post.contribution_count));
    actions.appendChild(commentSummary);
    if (owner || post.demo) actions.appendChild(primaryRespondControl(post, 'conversation'));
    return actions;
  }

  function cardNode(post, compact) {
    var card = el('article', 'cv1-card');
    if (post.demo) card.classList.add('cv1-card--demo');
    card.dataset.postKey = post.key;
    card._communityPost = post;
    var head = el('header', 'cv1-card-head');
    head.appendChild(avatar(post.author));
    var who = el('div');
    var authorLine = el('p', 'cv1-card-author', post.author.display_name);
    if (post.demo) authorLine.appendChild(el('span', 'cv1-demo-badge', 'Demo'));
    who.appendChild(authorLine);
    var meta = el('span', 'cv1-card-meta', relativeTime(post.published_at_utc) + ' · ' + (post.demo ? 'Illustrative demo' : (compact ? post.audience : 'Community')));
    if (post.edited_at_utc) meta.appendChild(el('span', 'cv1-card-tag', 'Edited'));
    who.appendChild(meta);
    head.appendChild(who);
    if (owner && !post.demo) head.appendChild(postOwnerControls(post, compact ? 'conversation' : 'feed'));
    card.appendChild(head);

    if (!compact) {
      card.dataset.primaryFeedCard = '';
      var copy = primaryPostCopy(post.body);
      var title = el('h2', 'cv1-card-title');
      var titleLink = el('a', '', copy.title);
      titleLink.href = post.permalink;
      titleLink.dataset.action = 'conversation';
      titleLink.dataset.postKey = post.key;
      title.appendChild(titleLink);
      card.appendChild(title);
      if (copy.supporting) card.appendChild(el('p', 'cv1-card-body cv1-card-supporting', copy.supporting));
      if (post.attachments && post.attachments.length) {
        card.appendChild(attachmentsNode(post.attachments, {
          permalink: post.permalink,
          postKey: post.key,
          title: copy.title
        }));
      }
      var primaryActions = el('div', 'cv1-card-actions cv1-card-actions--primary');
      var comment = el('a', 'cv1-icon-action cv1-comment-trigger');
      comment.href = post.permalink;
      comment.dataset.action = 'conversation';
      comment.dataset.postKey = post.key;
      comment.setAttribute(
        'aria-label',
        'Open conversation: ' + copy.title + ' · ' + post.contribution_count + (post.contribution_count === 1 ? ' comment' : ' comments')
      );
      comment.appendChild(cardActionIcon('comment'));
      comment.appendChild(el('span', 'cv1-action-count', post.contribution_count));
      primaryActions.appendChild(comment);
      if (owner || post.demo) primaryActions.appendChild(primaryRespondControl(post));
      card.appendChild(primaryActions);
      if (owner || post.demo) card.appendChild(primaryCommentComposer(post));
      var primaryShelf = renderConversationShelf(post);
      if (primaryShelf) card.appendChild(primaryShelf);
      return card;
    }

    var conversationCopy = primaryPostCopy(post.body);
    card.appendChild(el('h2', 'cv1-card-title', conversationCopy.title));
    if (conversationCopy.supporting) {
      card.appendChild(el('p', 'cv1-card-body cv1-card-supporting', conversationCopy.supporting));
    }
    if (post.attachments && post.attachments.length) {
      card.appendChild(attachmentsNode(post.attachments));
    }
    card.appendChild(conversationPostControls(post));
    return card;
  }

  function selectedParentContextNode(post) {
    var context = el('details', 'cv1-selected-parent');
    context.open = true;
    context.dataset.postKey = post.key;
    context._communityPost = post;
    var head = el('summary', 'cv1-card-head');
    head.appendChild(avatar(post.author));
    var who = el('div');
    who.appendChild(el('p', 'cv1-card-author', post.author.display_name));
    who.appendChild(el('span', 'cv1-card-meta', 'Reply to ' + post.author.display_name + ' · ' + (post.conversation_label || 'Community conversation')));
    head.appendChild(who);
    context.appendChild(head);
    context.appendChild(el('p', 'cv1-selected-parent__body', post.body));
    if (post.attachments && post.attachments.length) {
      context.appendChild(el('small', 'cv1-selected-parent__media', post.attachments.length + (post.attachments.length === 1 ? ' attachment' : ' attachments') + ' on the original post'));
    }
    context.appendChild(button('View original', 'view-original', 'cv1-selected-parent__action'));
    return context;
  }

  function feedTerminal(kind, title, body, searchMode) {
    disposeCommunityVoiceControllers('feed');
    feedList.replaceChildren();
    feedList.setAttribute('aria-busy', 'false');
    var panel = el('div', searchMode ? 'cv1-search-terminal' : (kind === 'error' ? 'cv1-unavailable' : 'cv1-empty'));
    if (searchMode && kind === 'error') panel.classList.add('cv1-search-terminal--error');
    panel.appendChild(terminalSymbol(kind === 'error' ? 'unavailable' : (searchMode ? 'search' : 'empty')));
    panel.appendChild(el('strong', '', title));
    panel.appendChild(el('p', '', body));
    var actions = el('div', searchMode ? 'cv1-search-terminal-actions' : '');
    if (kind === 'error') {
      actions.appendChild(button('Try again', searchMode ? 'retry-search' : 'retry-feed', 'cv1-primary'));
    } else if (owner && !searchMode) {
      actions.appendChild(button('Write a post', 'write', 'cv1-primary'));
    }
    if (searchMode) {
      var back = button('Back to Feed', 'back-to-feed', 'cv1-back-to-feed');
      actions.appendChild(back);
    }
    if (actions.childNodes.length) panel.appendChild(actions);
    feedList.appendChild(panel);
  }

  function renderFeed(items, append) {
    if (!append) {
      disposeCommunityVoiceControllers('feed');
      feedList.replaceChildren();
    }
    items.forEach(function (post) { feedList.appendChild(cardNode(post, false)); });
    feedList.setAttribute('aria-busy', 'false');
  }

  function searchResultNode(post) {
    var card = el('article', 'cv1-card cv1-search-result');
    card.dataset.postKey = post.key;
    card._communityPost = post;
    var head = el('header', 'cv1-card-head');
    head.appendChild(avatar(post.author));
    var who = el('div');
    who.appendChild(el('p', 'cv1-card-author', post.author.display_name));
    who.appendChild(el('span', 'cv1-card-meta', relativeTime(post.published_at_utc) + ' · ' + post.audience));
    head.appendChild(who);
    card.appendChild(head);
    card.appendChild(el('p', 'cv1-card-body', post.body));
    if (post.attachments && post.attachments.length) {
      var attachmentCue = compactAttachmentCue(post);
      attachmentCue.classList.add('cv1-search-attachment');
      card.appendChild(attachmentCue);
    }
    var open = el('a', 'cv1-secondary cv1-search-result__open', 'Open post');
    open.href = post.permalink;
    open.dataset.action = 'conversation';
    card.appendChild(open);
    return card;
  }

  function renderSearchResults(items) {
    disposeCommunityVoiceControllers('feed');
    feedList.replaceChildren();
    var heading = el('div', 'cv1-search-results-head');
    heading.appendChild(el('h2', '', 'Search Community'));
    heading.appendChild(button('Clear search', 'back-to-feed', 'cv1-link-button'));
    feedList.appendChild(heading);
    items.forEach(function (post) { feedList.appendChild(searchResultNode(post)); });
    feedList.setAttribute('aria-busy', 'false');
  }

  function partialFeedFailure() {
    var old = feedList.querySelector('[data-feed-partial-error]');
    if (old) old.remove();
    var panel = el('div', 'cv1-unavailable cv1-feed-partial-error');
    panel.dataset.feedPartialError = '';
    panel.appendChild(el('strong', '', 'More posts could not load'));
    panel.appendChild(el('p', '', 'The posts already shown are still available.'));
    var retry = button('Try again', 'retry-feed', 'cv1-primary');
    retry.dataset.append = 'true';
    panel.appendChild(retry);
    feedList.appendChild(panel);
    feedList.setAttribute('aria-busy', 'false');
  }

  function loadFeed(append) {
    if (state.loading) return;
    state.loading = true;
    if (!append) feedList.setAttribute('aria-busy', 'true');
    var url = '/api/v1/community/feed';
    if (append && state.cursor) url += '?cursor=' + encodeURIComponent(state.cursor);
    api(url).then(function (payload) {
      if (demoNote && !append) demoNote.hidden = !payload.demo_mode;
      if (!append) {
        app.dataset.demoMode = payload.demo_mode ? 'true' : 'false';
        if (demoQuickCompose) demoQuickCompose.hidden = !payload.demo_mode;
        if (owner && quickCompose) quickCompose.hidden = Boolean(payload.demo_mode);
      }
      var partial = feedList.querySelector('[data-feed-partial-error]');
      if (partial) partial.remove();
      if (!append && !payload.items.length) {
        feedTerminal('empty', owner ? 'Your community starts here' : 'No public posts yet', owner ? 'Share a question, small win, or update when you’re ready.' : 'Check back after the first public post is published.', false);
      } else {
        renderFeed(payload.items, append);
      }
      state.cursor = payload.next_cursor;
      loadMore.hidden = !state.cursor;
      feedEnd.hidden = Boolean(state.cursor) || (!append && !payload.items.length);
    }).catch(function () {
      if (append && feedList.querySelector('[data-post-key]')) partialFeedFailure();
      else feedTerminal('error', 'Community is unavailable', 'Nothing was published or lost. Try again when you’re ready.', false);
      loadMore.hidden = true;
      feedEnd.hidden = true;
    }).finally(function () { state.loading = false; });
  }

  function backToFeed() {
    state.searchRequest += 1;
    state.lastSearch = '';
    searchInput.value = '';
    clearSearch.hidden = true;
    app.classList.remove('cv1-is-searching');
    app.classList.remove('cv1-search-error');
    document.body.classList.remove('community-search-active');
    state.cursor = null;
    loadFeed(false);
    searchInput.focus();
  }

  function search(query) {
    var clean = query.trim();
    app.classList.toggle('cv1-is-searching', Boolean(clean));
    app.classList.remove('cv1-search-error');
    document.body.classList.toggle('community-search-active', Boolean(clean));
    clearSearch.hidden = !clean;
    if (!clean) { backToFeed(); return; }
    if (clean.length < 2) {
      feedList.setAttribute('aria-busy', 'false');
      return;
    }
    state.lastSearch = clean;
    state.searchRequest += 1;
    var requestNumber = state.searchRequest;
    feedList.setAttribute('aria-busy', 'true');
    api('/api/v1/community/search', jsonOptions('POST', {query: clean})).then(function (payload) {
      if (requestNumber !== state.searchRequest) return;
      app.classList.remove('cv1-search-error');
      if (demoNote) demoNote.hidden = !payload.demo_mode;
      app.dataset.demoMode = payload.demo_mode ? 'true' : 'false';
      if (demoQuickCompose) demoQuickCompose.hidden = !payload.demo_mode;
      if (owner && quickCompose) quickCompose.hidden = Boolean(payload.demo_mode);
      state.cursor = null;
      loadMore.hidden = true;
      feedEnd.hidden = true;
      if (!payload.items.length) feedTerminal('empty', 'No matching posts', 'Try another phrase or return to your Feed.', true);
      else renderSearchResults(payload.items);
    }).catch(function () {
      if (requestNumber !== state.searchRequest) return;
      app.classList.add('cv1-search-error');
      feedTerminal('error', 'Search is unavailable', 'Your Feed is still available.', true);
    }).finally(function () {
      if (requestNumber === state.searchRequest) feedList.setAttribute('aria-busy', 'false');
    });
  }

  function draftStatus(saved) {
    var node = app.querySelector('[data-draft-status]');
    if (node) node.hidden = !saved;
  }

  function saveDraft() {
    if (!owner || state.editPost || !draftKey) return;
    var body = formField(composerForm, 'body').value;
    var value = {
      body: body,
      intent: formField(composerForm, 'intent').value,
      response_posture: formField(composerForm, 'response_posture').value
    };
    try {
      if (body.trim()) {
        value.saved_at = Date.now();
        localStorage.setItem(draftKey, JSON.stringify(value));
        draftStatus(true);
      } else {
        localStorage.removeItem(draftKey);
        if (postCommandStorageKey) localStorage.removeItem(postCommandStorageKey);
        draftStatus(false);
      }
    } catch (ignore) { draftStatus(false); }
  }

  function restoreDraft() {
    draftStatus(false);
    if (!draftKey) return;
    try {
      var value = JSON.parse(localStorage.getItem(draftKey) || '{}');
      if (draftHasExpired(value)) {
        localStorage.removeItem(draftKey);
        if (postCommandStorageKey) localStorage.removeItem(postCommandStorageKey);
        return;
      }
      if (typeof value.body === 'string') formField(composerForm, 'body').value = value.body;
      if (['post', 'question', 'small_win'].indexOf(value.intent) >= 0) formField(composerForm, 'intent').value = value.intent;
      if (['open_feedback', 'questions_welcome', 'sharing_only', 'help_welcome'].indexOf(value.response_posture) >= 0) formField(composerForm, 'response_posture').value = value.response_posture;
      draftStatus(Boolean(value.body && value.body.trim()));
    } catch (ignore) { draftStatus(false); }
  }

  function updateCount() {
    var count = formField(composerForm, 'body').value.length;
    app.querySelector('[data-character-count]').textContent = count.toLocaleString() + ' / 4,000';
    updatePublishState();
  }

  function updatePublishState() {
    if (!composerForm) return;
    var publishControl = app.querySelector('[data-publish]');
    var editing = Boolean(state.editPost);
    var bodyReady = Boolean(formField(composerForm, 'body').value.trim());
    var audienceReady = editing || formField(composerForm, 'audience').value === 'public';
    var mediaReady = editing || state.attachments.every(function (item) { return item.state === 'ready'; });
    publishControl.disabled = !(bodyReady && audienceReady && mediaReady);
    publishControl.textContent = editing ? 'Save changes' : 'Review public post';
  }

  function setEditAttachmentMode(editing) {
    app.querySelectorAll('[data-composer-attachment-control]').forEach(function (node) {
      node.hidden = editing;
    });
    var input = app.querySelector('[data-attachment-input]');
    if (input) input.disabled = editing;
    var note = app.querySelector('[data-edit-attachment-note]');
    if (note) note.hidden = !editing;
  }

  function releaseUploadPreviews(items) {
    (items || []).forEach(function (item) {
      if (item._previewUrl) {
        URL.revokeObjectURL(item._previewUrl);
        item._previewUrl = null;
      }
    });
  }

  function resetComposer() {
    if (composerVoiceController) composerVoiceController.discard(false);
    composerForm.reset();
    formField(composerForm, 'audience').value = '';
    formField(composerForm, 'audience').disabled = false;
    releaseUploadPreviews(state.attachments);
    state.attachments = [];
    state.editPost = null;
    state.sparkPrompt = null;
    state.postCommandKey = null;
    state.postPayloadFingerprint = null;
    app.querySelector('[data-attachment-list]').replaceChildren();
    app.querySelector('[data-composer-error]').hidden = true;
    app.querySelector('#cv1-composer-title').textContent = 'New Community post';
    app.querySelector('[data-composer-body-label]').textContent = 'What’s on your mind?';
    app.querySelector('[data-spark-context]').hidden = true;
    setEditAttachmentMode(false);
    draftStatus(false);
    updateCount();
  }

  function restoreComposerHome() {
    if (!composer || !composerPlaceholder.parentNode) return;
    composer.classList.remove('cv1-composer-inline');
    composerPlaceholder.parentNode.insertBefore(composer, composerPlaceholder.nextSibling);
  }

  function presentComposer() {
    if (mobilePresentation()) {
      restoreComposerHome();
      composer.showModal();
    } else {
      var main = app.querySelector('.cv1-main');
      var anchor = quickCompose || feedList;
      main.insertBefore(composer, anchor);
      if (quickCompose) quickCompose.hidden = true;
      composer.classList.add('cv1-composer-inline');
      composer.show();
      composer.scrollIntoView({block: 'nearest'});
    }
  }

  function mobilePresentation() {
    return window.matchMedia('(max-width: 620px), (max-height: 520px) and (max-width: 950px)').matches;
  }

  function closeComposer() {
    if (composerVoiceController) composerVoiceController.discard(false);
    if (composer && composer.open) composer.close();
    if (quickCompose) quickCompose.hidden = app.dataset.demoMode === 'true';
    if (demoQuickCompose) demoQuickCompose.hidden = app.dataset.demoMode !== 'true';
    restoreComposerHome();
  }

  function openComposer(intent, sparkPrompt, focusAudience) {
    if (!owner) return;
    if (composer.open) {
      closeComposer();
      window.setTimeout(function () { openComposer(intent, sparkPrompt, focusAudience); }, 0);
      return;
    }
    resetComposer();
    restoreDraft();
    if (intent) formField(composerForm, 'intent').value = intent;
    state.sparkPrompt = sparkPrompt || null;
    if (state.sparkPrompt) {
      app.querySelector('[data-spark-context-prompt]').textContent = state.sparkPrompt;
      app.querySelector('[data-spark-context]').hidden = false;
      app.querySelector('[data-composer-body-label]').textContent = state.sparkPrompt;
    }
    formField(composerForm, 'audience').value = '';
    updateCount();
    presentComposer();
    if (focusAudience) {
      formField(composerForm, 'audience').focus();
    } else if (mobilePresentation()) {
      var composerTitle = app.querySelector('#cv1-composer-title');
      composerTitle.tabIndex = -1;
      composerTitle.focus();
      composer.querySelector('.cv1-dialog-frame').scrollTop = 0;
    } else {
      formField(composerForm, 'body').focus();
    }
  }

  function openEdit(post) {
    resetComposer();
    state.editPost = post;
    app.querySelector('#cv1-composer-title').textContent = 'Edit Community post';
    formField(composerForm, 'body').value = post.body;
    formField(composerForm, 'intent').value = post.intent;
    formField(composerForm, 'response_posture').value = post.response_posture;
    formField(composerForm, 'audience').value = 'public';
    formField(composerForm, 'audience').disabled = true;
    setEditAttachmentMode(true);
    updateCount();
    presentComposer();
    if (mobilePresentation()) {
      var editTitle = app.querySelector('#cv1-composer-title');
      editTitle.tabIndex = -1;
      editTitle.focus();
      composer.querySelector('.cv1-dialog-frame').scrollTop = 0;
    } else {
      formField(composerForm, 'body').focus();
    }
  }

  function uploadStateLabel(item) {
    if (item.state === 'ready') return 'Ready';
    if (item.state === 'rejected') return 'Rejected';
    if (item.state === 'failed') return 'Upload failed';
    if (item.state === 'uploading') return 'Uploading…';
    return 'Processing…';
  }

  function renderUploadList(items, list, reply) {
    list.replaceChildren();
    items.forEach(function (item) {
      var row = el('div', 'cv1-upload-row');
      row.dataset.uploadId = item._localId;
      var isImage = Boolean(item._previewUrl);
      if (isImage) {
        var preview = el('img', 'cv1-upload-row__preview');
        preview.src = item._previewUrl;
        preview.alt = '';
        row.appendChild(preview);
      } else {
        var fileIcon = el('span', 'cv1-upload-row__file-icon', '▱');
        fileIcon.setAttribute('aria-hidden', 'true');
        row.appendChild(fileIcon);
      }
      var details = el('span', 'cv1-upload-row__details');
      details.appendChild(el('strong', '', item.display_name));
      var stateLine = el('span', 'cv1-upload-row__state', uploadStateLabel(item));
      if (item.state === 'uploading' || item.state === 'processing') stateLine.dataset.processing = '';
      details.appendChild(stateLine);
      row.appendChild(details);
      var actions = el('span', 'cv1-upload-row__actions');
      if (item.state === 'failed' && item._file) {
        var retry = button('Try again', reply ? 'retry-reply-upload' : 'retry-upload');
        retry.dataset.uploadId = item._localId;
        actions.appendChild(retry);
      }
      var remove = button('Remove', reply ? 'remove-reply-upload' : 'remove-upload');
      remove.dataset.uploadId = item._localId;
      remove.setAttribute('aria-label', 'Remove ' + item.display_name);
      actions.appendChild(remove);
      row.appendChild(actions);
      list.appendChild(row);
    });
  }

  function renderUploads() {
    renderUploadList(state.attachments, app.querySelector('[data-attachment-list]'), false);
    updatePublishState();
  }

  function renderReplyUploads() {
    var list = app.querySelector('[data-reply-attachment-list]');
    if (list) renderUploadList(state.replyAttachments, list, true);
    resizeReplyComposer();
  }

  function pollUpload(item, attempts, renderer) {
    if (attempts > 120) { item.state = 'failed'; renderer(); return; }
    window.setTimeout(function () {
      if (!item.key) return;
      api('/api/v1/community/attachments/' + encodeURIComponent(item.key) + '/status', jsonOptions('POST', {})).then(function (payload) {
        Object.assign(item, payload.attachment);
        renderer();
        if (item.state === 'processing') pollUpload(item, attempts + 1, renderer);
      }).catch(function () { item.state = 'failed'; renderer(); });
    }, 2500);
  }

  function uploadFile(file, items, renderer) {
    if (!file || items.length >= 4) { showToast('Up to four attachments are allowed.', true); return; }
    var item = {
      _localId: uuid(),
      _file: file,
      _previewUrl: file.type && file.type.indexOf('image/') === 0 ? URL.createObjectURL(file) : null,
      display_name: file.name || 'Attachment',
      state: 'uploading',
      key: null
    };
    items.push(item);
    renderer();
    var data = new FormData();
    data.append('file', file);
    api('/api/v1/community/attachments', {method: 'POST', headers: {'X-PeerSlate-Request': 'same-origin'}, body: data})
      .then(function (payload) {
        Object.assign(item, payload.attachment);
        renderer();
        pollUpload(item, 0, renderer);
      }).catch(function (error) {
        item.state = 'failed';
        item.error = error.message;
        renderer();
      });
  }

  function removeUpload(items, uploadId, renderer, retry) {
    var item = items.find(function (candidate) { return candidate._localId === uploadId; });
    if (!item) return;
    var file = item._file;
    var cleanup = item.key
      ? api('/api/v1/community/attachments/' + encodeURIComponent(item.key), jsonOptions('DELETE', {})).catch(function () {})
      : Promise.resolve();
    cleanup.finally(function () {
      releaseUploadPreviews([item]);
      items.splice(items.indexOf(item), 1);
      renderer();
      if (retry && file) uploadFile(file, items, renderer);
    });
  }

  function stableCommandKey(payload, kind, scopeKey) {
    var fingerprint = (scopeKey ? String(scopeKey) + '|' : '') + JSON.stringify(payload);
    var signature = payloadSignature(fingerprint);
    var keyField = kind + 'CommandKey';
    var fingerprintField = kind + 'PayloadFingerprint';
    var commandStorageKey = kind === 'post'
      ? postCommandStorageKey
      : (kind === 'reply' ? replyCommandStorageKey : null);
    if (commandStorageKey && !state[keyField]) {
      try {
        var pending = JSON.parse(localStorage.getItem(commandStorageKey) || '{}');
        if (pending.signature === signature && typeof pending.key === 'string') {
          state[keyField] = pending.key;
          state[fingerprintField] = fingerprint;
        } else if (pending.key) {
          localStorage.removeItem(commandStorageKey);
        }
      } catch (ignorePendingCommand) {
        try { localStorage.removeItem(commandStorageKey); } catch (ignoreInvalidPendingCommand) {}
      }
    }
    if (state[keyField] && state[fingerprintField] !== fingerprint) {
      if (commandStorageKey) {
        try { localStorage.removeItem(commandStorageKey); } catch (ignoreChangedCommand) {}
      }
      state[keyField] = null;
      state[fingerprintField] = null;
    }
    if (!state[keyField]) {
      state[keyField] = uuid();
      state[fingerprintField] = fingerprint;
    }
    if (commandStorageKey) {
      try { localStorage.setItem(commandStorageKey, JSON.stringify({key: state[keyField], signature: signature})); } catch (ignorePendingWrite) {}
    }
    return state[keyField];
  }

  function payloadSignature(value) {
    var hash = 2166136261;
    for (var index = 0; index < value.length; index += 1) {
      hash ^= value.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return ('00000000' + (hash >>> 0).toString(16)).slice(-8) + ':' + value.length;
  }

  function showPublicationBanner() {
    if (!publicationBanner) return;
    if (mobilePresentation()) {
      app.insertBefore(publicationBanner, app.firstElementChild);
    } else {
      var main = app.querySelector('.cv1-main');
      main.insertBefore(publicationBanner, main.firstElementChild.nextSibling);
    }
    publicationBanner.hidden = false;
    publicationBanner.scrollIntoView({block: 'nearest'});
  }

  function composerReadyForSubmission() {
    var errorNode = app.querySelector('[data-composer-error]');
    errorNode.hidden = true;
    if (state.attachments.some(function (item) { return item.state !== 'ready'; })) {
      errorNode.textContent = 'Wait until every attachment is ready, retry it, or remove it.';
      errorNode.hidden = false;
      return false;
    }
    if (!state.editPost && formField(composerForm, 'audience').value !== 'public') {
      errorNode.textContent = 'Select Public before reviewing this post.';
      errorNode.hidden = false;
      return false;
    }
    if (!formField(composerForm, 'body').value.trim()) return false;
    return true;
  }

  function composerVoiceReadyForSubmission() {
    if (!composerVoiceController || !composerVoiceController.hasUnresolvedVoice()) return true;
    var errorNode = app.querySelector('[data-composer-error]');
    errorNode.textContent = 'Finish or discard the Voice review before continuing.';
    errorNode.hidden = false;
    composerVoiceController.focusTrigger();
    return false;
  }

  function openPublicConfirmation() {
    if (!publicConfirmation || !composerReadyForSubmission() || !composerVoiceReadyForSubmission()) return;
    publicConfirmation.showModal();
    var confirmControl = publicConfirmation.querySelector('[data-confirm-publication]');
    if (confirmControl) confirmControl.focus();
  }

  function closePublicConfirmation() {
    state.publicationConfirming = false;
    if (!publicConfirmation || !publicConfirmation.open) return;
    var confirmControl = publicConfirmation.querySelector('[data-confirm-publication]');
    if (confirmControl) confirmControl.disabled = false;
    publicConfirmation.close();
  }

  function submitComposerMutation() {
    if (!composerReadyForSubmission() || !composerVoiceReadyForSubmission()) return;
    var errorNode = app.querySelector('[data-composer-error]');
    var payload = {
      body: formField(composerForm, 'body').value,
      intent: formField(composerForm, 'intent').value,
      response_posture: formField(composerForm, 'response_posture').value
    };
    var request;
    var editing = Boolean(state.editPost);
    if (editing) {
      payload.expected_revision = state.editPost.revision;
      request = api('/api/v1/community/posts/' + encodeURIComponent(state.editPost.key), jsonOptions('PATCH', payload));
    } else {
      payload.audience = formField(composerForm, 'audience').value;
      payload.attachment_keys = state.attachments.map(function (item) { return item.key; });
      request = api('/api/v1/community/posts', jsonOptions('POST', payload, stableCommandKey(payload, 'post')));
    }
    app.querySelector('[data-publish]').disabled = true;
    request.then(function () {
      if (composerVoiceController) composerVoiceController.discard(false);
      if (draftKey) {
        try { localStorage.removeItem(draftKey); } catch (ignore) {}
      }
      if (postCommandStorageKey) {
        try { localStorage.removeItem(postCommandStorageKey); } catch (ignoreCommand) {}
      }
      state.postCommandKey = null;
      state.postPayloadFingerprint = null;
      closePublicConfirmation();
      closeComposer();
      if (editing) showToast('Post updated.');
      else showPublicationBanner();
      state.cursor = null;
      loadFeed(false);
    }).catch(function (error) {
      closePublicConfirmation();
      errorNode.textContent = error.message + ' You can try again without creating a duplicate.';
      errorNode.hidden = false;
    }).finally(updatePublishState);
  }

  function publish(event) {
    event.preventDefault();
    if (state.editPost) {
      submitComposerMutation();
      return;
    }
    openPublicConfirmation();
  }

  function confirmPublicPublication() {
    if (state.editPost || state.publicationConfirming || !publicConfirmation) return;
    state.publicationConfirming = true;
    var confirmControl = publicConfirmation.querySelector('[data-confirm-publication]');
    if (confirmControl) confirmControl.disabled = true;
    submitComposerMutation();
  }

  function tombstoneNode(item) {
    var node = el('article');
    node.dataset.contributionTombstone = '';
    node.dataset.contributionKey = item.key;
    var messages = {
      deleted: ['Contribution deleted', 'This contribution was deleted.'],
      held: ['Contribution under review', 'This contribution is temporarily unavailable while it is reviewed.'],
      removed: ['Contribution removed', 'This contribution was removed.'],
      source_unavailable: ['Contribution unavailable', 'This contribution is unavailable because its source account is no longer active.']
    };
    var message = messages[item.state] || ['Contribution unavailable', 'This contribution is no longer available.'];
    node.dataset.state = item.state === 'held' ? 'held' : (item.state === 'deleted' ? 'deleted' : 'revoked');
    node.appendChild(el('strong', '', message[0]));
    node.appendChild(el('span', '', message[1]));
    return node;
  }

  function contributionOwnerOverflow(item) {
    var overflow = el('details', 'cv1-contribution-owner-controls');
    var overflowTrigger = el('summary', '', '•••');
    overflowTrigger.setAttribute('aria-label', 'Reply actions');
    overflow.appendChild(overflowTrigger);
    var overflowMenu = el('div', 'cv1-contribution-owner-actions');
    var edit = button('Edit', 'edit-contribution');
    edit.dataset.key = item.key;
    edit.dataset.revision = item.revision;
    overflowMenu.appendChild(edit);
    var remove = button('Delete', 'delete-contribution', 'cv1-delete');
    remove.dataset.key = item.key;
    remove.dataset.revision = item.revision;
    overflowMenu.appendChild(remove);
    overflow.appendChild(overflowMenu);
    return overflow;
  }

  function appendReplyAction(actions, item, label) {
    if (Number(item.depth || 0) >= maximumReplyDepth) {
      var limit = el('span', 'cv1-reply-depth-limit', 'Maximum reply depth reached. Add a top-level update instead.');
      limit.dataset.replyDepthLimit = '';
      limit.setAttribute('role', 'status');
      actions.appendChild(limit);
      return;
    }
    var reply = button(label, 'reply-to');
    reply.dataset.key = item.key;
    actions.appendChild(reply);
  }

  function contributionNode(item, standardActions) {
    if (item.state && item.state !== 'active') return tombstoneNode(item);
    var node = el('article', 'cv1-contribution');
    node.dataset.depth = Math.min(3, item.depth || 0);
    node.dataset.contributionKey = item.key;
    node._communityContribution = item;
    if (state.conversationFocusKey === item.key) {
      node.dataset.conversationFocus = '';
      node.tabIndex = -1;
    }
    var head = el('div', 'cv1-card-head');
    head.appendChild(avatar(item.author));
    var copy = el('div');
    copy.appendChild(el('p', 'cv1-card-author', item.author.display_name));
    copy.appendChild(el('span', 'cv1-card-meta', relativeTime(item.created_at_utc) + (item.kind === 'author_update' ? ' · Author update' : '') + (item.edited_at_utc ? ' · Edited' : '')));
    head.appendChild(copy);
    var demoConversation = Boolean(state.currentPost && state.currentPost.demo);
    if (owner && !demoConversation && !item.demo && standardActions === 'overflow-only') head.appendChild(contributionOwnerOverflow(item));
    node.appendChild(head);
    node.appendChild(el('p', 'cv1-contribution-body', item.body));
    if (item.attachments && item.attachments.length) {
      node.appendChild(attachmentsNode(item.attachments));
    }
    if (owner && !demoConversation && !item.demo && standardActions !== false && standardActions !== 'overflow-only') {
      var actions = el('div', 'cv1-owner-menu');
      appendReplyAction(actions, item, 'Reply');
      actions.appendChild(contributionOwnerOverflow(item));
      node.appendChild(actions);
    }
    return node;
  }

  function appendContributionTree(container, items) {
    var byKey = {};
    var children = {};
    items.forEach(function (item) { byKey[item.key] = item; });
    items.forEach(function (item) {
      if (item.parent_key && byKey[item.parent_key]) {
        if (!children[item.parent_key]) children[item.parent_key] = [];
        children[item.parent_key].push(item);
      }
    });
    function appendItem(item, target) {
      target.appendChild(contributionNode(item, true));
      var replies = children[item.key] || [];
      replies.slice(0, 2).forEach(function (reply) { appendItem(reply, target); });
      if (replies.length > 2) {
        var more = button('View ' + (replies.length - 2) + ' more ' + (replies.length - 2 === 1 ? 'reply' : 'replies'), null, 'cv1-secondary cv1-view-replies');
        more.addEventListener('click', function () {
          var fragment = document.createDocumentFragment();
          replies.slice(2).forEach(function (reply) { appendItem(reply, fragment); });
          more.replaceWith(fragment);
        });
        target.appendChild(more);
      }
    }
    var roots = items.filter(function (item) { return !item.parent_key || !byKey[item.parent_key]; });
    roots.forEach(function (item) { appendItem(item, container); });
  }

  function renderConversationHeaderActions(post, selected) {
    conversationHeaderActions.replaceChildren();
    conversationHeaderActions.dataset.postKey = post.key;
    conversationHeaderActions._communityPost = post;
  }

  function mergeSelectedConversationContext(post) {
    var all = (post.contributions || []).slice();
    var seen = {};
    all.forEach(function (item) { seen[item.key] = true; });
    (state.selectedAncestors || []).concat(state.selectedContribution ? [state.selectedContribution] : []).forEach(function (item) {
      if (!item || seen[item.key]) return;
      seen[item.key] = true;
      all.push(item);
    });
    post.contributions = all;
  }

  function selectedConversationContext(selected) {
    var notice = el('aside', 'cv1-conversation-focus-note');
    notice.dataset.selectedConversationContext = '';
    notice.setAttribute('role', 'status');
    notice.appendChild(el('strong', '', 'Selected reply'));
    notice.appendChild(el('span', '', 'From ' + selected.author.display_name + ' · the full conversation remains below.'));
    return notice;
  }

  function renderConversation(post) {
    state.currentPost = post;
    var selected = state.conversationFocusKey && state.selectedContribution && state.selectedContribution.key === state.conversationFocusKey
      ? state.selectedContribution
      : null;
    mergeSelectedConversationContext(post);
    app.querySelector('#cv1-conversation-title').textContent = post.conversation_label;
    app.querySelector('[data-conversation-meta]').textContent = selected
      ? 'Selected reply from ' + selected.author.display_name + ' · full conversation'
      : 'Started by ' + post.author.display_name + ' · ' + relativeTime(post.published_at_utc) + ' · Community';
    renderConversationHeaderActions(post, selected);
    conversationBody.setAttribute('aria-busy', 'false');
    conversationBody.replaceChildren();
    var root = cardNode(post, true);
    root.classList.add('cv1-thread-root');
    root.tabIndex = -1;
    conversationBody.appendChild(root);
    if (selected && selected.state === 'active') conversationBody.appendChild(selectedConversationContext(selected));
    if (!post.contributions.length) conversationBody.appendChild(el('p', 'cv1-rail-copy', 'No replies yet.'));
    appendContributionTree(conversationBody, post.contributions);
    if (post.next_contribution_cursor) {
      var earlier = button('Load earlier replies', 'load-earlier', 'cv1-secondary');
      earlier.dataset.loadEarlier = '';
      conversationBody.appendChild(earlier);
    }
    if (post.demo) {
      if (replyVoiceController) replyVoiceController.discard(false);
      if (replyForm) replyForm.hidden = true;
    } else {
      prepareReplyComposer();
    }
    if (selected) {
      window.requestAnimationFrame(function () {
        var focusNode = conversationBody.querySelector('[data-contribution-key="' + CSS.escape(selected.key) + '"]');
        if (focusNode) {
          focusNode.focus({preventScroll: true});
          focusNode.scrollIntoView({block: 'center'});
        }
      });
    }
  }

  function detailSkeleton(selected) {
    var skeleton = el('div');
    skeleton.dataset.detailSkeleton = '';
    var status = el('p', 'cv1-loading-label', selected ? 'Loading reply…' : 'Loading conversation…');
    status.setAttribute('role', 'status');
    skeleton.appendChild(status);
    for (var index = 0; index < 4; index += 1) skeleton.appendChild(el('span'));
    return skeleton;
  }

  function backToFeedControl() {
    var back = button('Back to Feed', 'close-conversation', 'cv1-primary');
    return back;
  }

  function openConversation(postKey, pushHistory, focusKey, focusOriginal) {
    if (conversation.open && replyVoiceController) {
      saveReplyDraft();
      replyVoiceController.discard(false);
    }
    if (!conversation.open) {
      var focused = document.activeElement;
      var shelfTrack = focused && focused.closest ? focused.closest('[data-conversation-shelf-track]') : null;
      state.conversationReturn = {
        scrollY: window.scrollY,
        focusNode: focused,
        shelfTrack: shelfTrack,
        shelfScrollLeft: shelfTrack ? shelfTrack.scrollLeft : null
      };
    }
    var knownPost = state.currentPost && state.currentPost.key === postKey ? state.currentPost : null;
    var knownItems = knownPost
      ? (knownPost.contributions || []).concat(knownPost.preview_contributions || [])
      : [];
    var knownSelected = focusKey
      ? knownItems.find(function (item) { return item.key === focusKey; }) || null
      : null;
    state.conversationFocusKey = focusKey || null;
    state.selectedContribution = knownSelected;
    state.selectedAncestors = [];
    var requestNumber = ++state.conversationRequest;
    if (!conversation.open) conversation.showModal();
    if (replyForm) replyForm.hidden = Boolean(knownPost && knownPost.demo);
    if (knownPost) {
      app.querySelector('#cv1-conversation-title').textContent = knownPost.conversation_label;
      app.querySelector('[data-conversation-meta]').textContent = focusKey
        ? 'Selected reply · loading full conversation'
        : 'Started by ' + knownPost.author.display_name + ' · ' + relativeTime(knownPost.published_at_utc) + ' · Community';
      renderConversationHeaderActions(knownPost, knownSelected);
    } else {
      conversationHeaderActions.replaceChildren();
      app.querySelector('#cv1-conversation-title').textContent = 'Replies & updates';
      app.querySelector('[data-conversation-meta]').textContent = '';
    }
    conversationBody.setAttribute('aria-busy', 'true');
    conversationBody.replaceChildren();
    if (knownPost) {
      var loadingRoot = cardNode(knownPost, true);
      loadingRoot.classList.add('cv1-thread-root');
      conversationBody.appendChild(loadingRoot);
    }
    conversationBody.appendChild(detailSkeleton(Boolean(state.conversationFocusKey)));
    var postRequest = api('/api/v1/community/posts/' + encodeURIComponent(postKey));
    var selectedRequest = state.conversationFocusKey
      ? api('/api/v1/community/posts/' + encodeURIComponent(postKey) + '/contributions/' + encodeURIComponent(state.conversationFocusKey))
      : Promise.resolve(null);
    return Promise.all([postRequest, selectedRequest]).then(function (results) {
      if (requestNumber !== state.conversationRequest) return;
      var payload = results[0];
      var selectedPayload = results[1];
      if (selectedPayload) {
        state.selectedContribution = selectedPayload.contribution;
        state.selectedAncestors = selectedPayload.ancestors || [];
      }
      renderConversation(payload.post);
      if (pushHistory) {
        var historyPath = state.conversationFocusKey
          ? payload.post.permalink + '/contributions/' + encodeURIComponent(state.conversationFocusKey)
          : payload.post.permalink;
        history.pushState({
          communityPost: postKey,
          selectedContribution: state.conversationFocusKey,
          feedScrollY: state.conversationReturn && state.conversationReturn.scrollY,
          shelfScrollLeft: state.conversationReturn && state.conversationReturn.shelfScrollLeft
        }, '', historyPath);
        state.conversationPushed = true;
      }
      if (focusOriginal) {
        window.requestAnimationFrame(function () {
          var root = conversationBody.querySelector('.cv1-thread-root');
          if (root) root.focus();
        });
      }
    }).catch(function (error) {
      if (requestNumber !== state.conversationRequest) return;
      conversationBody.setAttribute('aria-busy', 'false');
      conversationHeaderActions.replaceChildren();
      if (replyForm) replyForm.hidden = true;
      app.querySelector('#cv1-conversation-title').textContent = focusKey ? 'Reply unavailable' : 'Conversation unavailable';
      app.querySelector('[data-conversation-meta]').textContent = '';
      conversationBody.replaceChildren();
      var unavailable = el('div', 'cv1-unavailable');
      unavailable.appendChild(terminalSymbol('lock'));
      unavailable.appendChild(el('strong', '', error.status === 404 ? (focusKey ? 'This reply is no longer available' : 'This post is no longer available') : 'Conversation is unavailable'));
      unavailable.appendChild(el('p', '', 'It may have been removed, restricted, or temporarily unavailable.'));
      unavailable.appendChild(backToFeedControl());
      conversationBody.appendChild(unavailable);
    });
  }

  function reloadConversation() {
    if (!state.currentPost) return;
    return openConversation(state.currentPost.key, false, state.conversationFocusKey, false);
  }

  function showFullConversation(focusOriginal) {
    if (!state.currentPost) return;
    var post = state.currentPost;
    var nextHistory = Object.assign({}, history.state || {}, {
      communityPost: post.key,
      selectedContribution: null
    });
    history.replaceState(nextHistory, '', post.permalink);
    openConversation(post.key, false, null, Boolean(focusOriginal));
  }

  function findContribution(contributionKey) {
    if (state.selectedContribution && state.selectedContribution.key === contributionKey) return state.selectedContribution;
    var selectedAncestor = state.selectedAncestors.find(function (item) { return item.key === contributionKey; });
    if (selectedAncestor) return selectedAncestor;
    return state.currentPost && state.currentPost.contributions
      ? state.currentPost.contributions.find(function (item) { return item.key === contributionKey; })
      : null;
  }

  function loadEarlierContributions(control) {
    if (!state.currentPost || !state.currentPost.next_contribution_cursor) return;
    control.disabled = true;
    control.textContent = 'Loading earlier replies…';
    var current = state.currentPost;
    api('/api/v1/community/posts/' + encodeURIComponent(current.key) + '?cursor=' + encodeURIComponent(current.next_contribution_cursor))
      .then(function (payload) {
        var combined = current.contributions.concat(payload.post.contributions);
        var seen = {};
        payload.post.contributions = combined.filter(function (item) {
          if (seen[item.key]) return false;
          seen[item.key] = true;
          return true;
        });
        renderConversation(payload.post);
      }).catch(function (error) {
        control.disabled = false;
        control.textContent = 'Try loading earlier replies again';
        showToast(error.message, true);
      });
  }

  function replyDraftStorageKey(postKey, parentKey) {
    return draftKey ? draftKey + ':reply-draft:' + postKey + ':' + (parentKey || 'top-level') : null;
  }

  function replyDraftStatus(saved) {
    var node = app.querySelector('[data-reply-draft-status]');
    if (node) node.hidden = !saved;
  }

  function resizeReplyComposer() {
    if (!replyForm) return;
    var input = formField(replyForm, 'body');
    var submit = replyForm.querySelector('[data-reply-send]');
    if (!input || !submit) return;
    input.style.height = 'auto';
    var nextHeight = Math.max(28, Math.min(input.scrollHeight, 168));
    input.style.height = nextHeight + 'px';
    input.style.overflowY = input.scrollHeight > 168 ? 'auto' : 'hidden';
    submit.disabled = replyForm.hasAttribute('data-submitting') || !input.value.trim() || state.replyAttachments.some(function (item) { return item.state !== 'ready'; });
  }

  function setupComposerVoiceController() {
    if (!composerForm) return;
    var input = formField(composerForm, 'body');
    var trigger = composerForm.querySelector('[data-composer-voice]');
    var panelHost = composerForm.querySelector('[data-composer-voice-panel-host]');
    var topTrigger = app.querySelector('[data-top-voice]');
    if (!input || !trigger || !panelHost) return;
    composerVoiceController = new CommunityVoiceController({
      form: composerForm,
      input: input,
      trigger: trigger,
      mirrors: topTrigger ? [topTrigger] : [],
      context: 'post',
      maxLength: 4000,
      noun: 'post',
      resize: updateCount,
      panelHost: panelHost,
      lifetime: 'page'
    });
    trigger.addEventListener('click', function () { composerVoiceController.start(); });
  }

  function renderDemoAttachments() {
    if (!demoComposerForm) return;
    var list = demoComposerForm.querySelector('[data-demo-attachment-list]');
    if (!list) return;
    list.replaceChildren();
    state.demoAttachments.forEach(function (item, index) {
      var row = el('div', 'cv1-demo-upload-row');
      if (item.previewUrl) {
        var preview = el('img', 'cv1-demo-upload-preview');
        preview.src = item.previewUrl;
        preview.alt = '';
        row.appendChild(preview);
      } else {
        row.appendChild(el('span', 'cv1-demo-upload-icon', item.kind === 'file' ? '⌇' : '▧'));
      }
      var copy = el('span', 'cv1-demo-upload-copy');
      copy.appendChild(el('strong', '', item.file.name));
      copy.appendChild(el('small', '', 'Local demo only · ' + Math.max(1, Math.round(item.file.size / 1024)) + ' KB'));
      row.appendChild(copy);
      var remove = button('Remove', '', 'cv1-demo-upload-remove');
      remove.dataset.demoRemoveAttachment = String(index);
      row.appendChild(remove);
      list.appendChild(row);
    });
  }

  function addDemoAttachment(file, kind) {
    if (!file) return;
    var allowed = kind === 'photo'
      ? ['image/jpeg', 'image/png']
      : ['application/pdf', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'];
    var xlsxByName = kind === 'file' && /\.xlsx$/i.test(file.name || '');
    if (allowed.indexOf(file.type) < 0 && !xlsxByName) {
      showToast('Choose a JPEG, PNG, PDF, or macro-free XLSX file for this demo.', true);
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      showToast('Choose a demo file smaller than 10 MB.', true);
      return;
    }
    if (state.demoAttachments.length >= 4) {
      showToast('This demo accepts up to four local examples.', true);
      return;
    }
    state.demoAttachments.push({
      file: file,
      kind: kind,
      previewUrl: kind === 'photo' ? URL.createObjectURL(file) : null
    });
    renderDemoAttachments();
    showToast('Local example added. It was not uploaded.');
  }

  function clearDemoAttachments() {
    state.demoAttachments.forEach(function (item) {
      if (item.previewUrl) URL.revokeObjectURL(item.previewUrl);
    });
    state.demoAttachments = [];
    renderDemoAttachments();
  }

  function openDemoComposer(startVoice) {
    if (!demoComposer || !demoComposerForm) return;
    if (!demoComposer.open) demoComposer.showModal();
    var body = formField(demoComposerForm, 'body');
    if (startVoice && demoComposerVoiceController) demoComposerVoiceController.start();
    else if (body) body.focus();
  }

  function closeDemoComposer() {
    if (demoComposerVoiceController) demoComposerVoiceController.discard(false);
    if (demoComposer && demoComposer.open) demoComposer.close();
  }

  function setupDemoComposer() {
    if (!demoComposerForm) return;
    var input = formField(demoComposerForm, 'body');
    var trigger = demoComposerForm.querySelector('[data-demo-composer-voice]');
    var topTrigger = app.querySelector('[data-demo-top-voice]');
    var panelHost = demoComposerForm.querySelector('[data-demo-composer-voice-panel-host]');
    var count = demoComposerForm.querySelector('[data-demo-character-count]');
    if (!input || !trigger || !panelHost) return;
    demoComposerVoiceController = new CommunityVoiceController({
      form: demoComposerForm,
      input: input,
      trigger: trigger,
      mirrors: topTrigger ? [topTrigger] : [],
      context: 'post',
      maxLength: 4000,
      noun: 'demo post',
      resize: function () {
        if (count) count.textContent = input.value.length.toLocaleString() + ' / 4,000';
      },
      panelHost: panelHost,
      lifetime: 'page',
      localOnly: !owner
    });
    input.addEventListener('input', function () {
      if (count) count.textContent = input.value.length.toLocaleString() + ' / 4,000';
    });
    trigger.addEventListener('click', function () { demoComposerVoiceController.start(); });
    demoComposerForm.addEventListener('submit', function (event) { event.preventDefault(); });
    demoComposerForm.querySelector('[data-demo-attachment-input]').addEventListener('change', function (event) {
      addDemoAttachment(event.target.files[0], 'file');
      event.target.value = '';
    });
    demoComposerForm.querySelector('[data-demo-photo-input]').addEventListener('change', function (event) {
      addDemoAttachment(event.target.files[0], 'photo');
      event.target.value = '';
    });
    demoComposerForm.querySelector('[data-demo-attachment-list]').addEventListener('click', function (event) {
      var remove = event.target.closest('[data-demo-remove-attachment]');
      if (!remove) return;
      var index = Number(remove.dataset.demoRemoveAttachment);
      var item = state.demoAttachments[index];
      if (item && item.previewUrl) URL.revokeObjectURL(item.previewUrl);
      state.demoAttachments.splice(index, 1);
      renderDemoAttachments();
    });
  }

  function setupReplyVoiceController() {
    if (!replyForm) return;
    var input = formField(replyForm, 'body');
    var trigger = replyForm.querySelector('[data-reply-voice]');
    var panelHost = replyForm.querySelector('[data-reply-voice-panel-host]');
    if (!input || !trigger || !panelHost) return;
    replyVoiceController = new CommunityVoiceController({
      form: replyForm,
      input: input,
      trigger: trigger,
      context: 'contribution',
      maxLength: 2000,
      noun: 'reply',
      resize: resizeReplyComposer,
      panelHost: panelHost,
      lifetime: 'page'
    });
    trigger.addEventListener('click', function () { replyVoiceController.start(); });
  }

  function saveReplyDraft() {
    if (!owner || !replyForm || !state.currentPost) return;
    var key = replyDraftStorageKey(state.currentPost.key, state.replyParentKey);
    if (!key) return;
    var value = formField(replyForm, 'body').value;
    try {
      if (value.trim()) {
        localStorage.setItem(key, JSON.stringify({ body: value, saved_at: Date.now() }));
        replyDraftStatus(true);
      } else {
        localStorage.removeItem(key);
        replyDraftStatus(false);
      }
    } catch (ignoreReplyDraft) { replyDraftStatus(false); }
  }

  function readReplyDraft(targetKey) {
    var raw = localStorage.getItem(targetKey);
    if (!raw) return '';
    // Replies saved before the expiry envelope existed are plain strings, and
    // are treated exactly as the primary comment surface treats them: undated,
    // preserved, and dated again on their next save.
    if (raw.charAt(0) !== '{') return raw;
    var value = JSON.parse(raw);
    if (draftHasExpired(value)) {
      localStorage.removeItem(targetKey);
      return '';
    }
    return typeof value.body === 'string' ? value.body : '';
  }

  function replyTargetCopy() {
    if (!state.replyParentKey) return 'Reply to conversation';
    var target = findContribution(state.replyParentKey);
    return target ? 'Replying to ' + target.author.display_name : 'Reply to conversation';
  }

  function restoreReplyDraft() {
    if (!replyForm || !state.currentPost) return;
    var input = formField(replyForm, 'body');
    var targetKey = replyDraftStorageKey(state.currentPost.key, state.replyParentKey);
    if (state.replyDraftTargetKey === targetKey) {
      resizeReplyComposer();
      return;
    }
    state.replyDraftTargetKey = targetKey;
    input.value = '';
    if (targetKey) {
      try { input.value = readReplyDraft(targetKey); } catch (ignoreStoredReply) {}
    }
    replyDraftStatus(Boolean(input.value.trim()));
    resizeReplyComposer();
  }

  function prepareReplyComposer() {
    if (!replyForm || !state.currentPost) return;
    if (state.currentPost.demo) {
      replyForm.hidden = true;
      return;
    }
    var target = state.replyParentKey ? findContribution(state.replyParentKey) : null;
    if (state.replyParentKey && (!target || Number(target.depth || 0) >= maximumReplyDepth)) {
      if (replyVoiceController) replyVoiceController.discard(false);
      state.replyParentKey = null;
    }
    var targetCopy = app.querySelector('[data-reply-target]');
    if (targetCopy) targetCopy.textContent = replyTargetCopy();
    replyForm.hidden = false;
    restoreReplyDraft();
  }

  function targetReply(item) {
    if (!item || Number(item.depth || 0) >= maximumReplyDepth) {
      showToast('Maximum reply depth reached. Add a top-level update instead.', true);
      return;
    }
    saveReplyDraft();
    if (replyVoiceController) replyVoiceController.discard(false);
    state.replyParentKey = item.key;
    state.replyDraftTargetKey = null;
    prepareReplyComposer();
    var input = formField(replyForm, 'body');
    if (input) input.focus();
  }

  function sendReply(event) {
    event.preventDefault();
    if (!state.currentPost || !replyForm) return;
    var form = event.currentTarget;
    var body = formField(form, 'body').value.trim();
    if (!body || form.hasAttribute('data-submitting')) return;
    if (state.replyAttachments.some(function (item) { return item.state !== 'ready'; })) {
      showToast('Wait until every reply attachment is ready, retry it, or remove it.', true);
      return;
    }
    var replyTarget = state.replyParentKey ? findContribution(state.replyParentKey) : null;
    if (replyTarget && Number(replyTarget.depth || 0) >= maximumReplyDepth) {
      showToast('Maximum reply depth reached. Add a top-level update instead.', true);
      return;
    }
    var payload = {body: body, parent_key: state.replyParentKey, attachment_keys: state.replyAttachments.map(function (item) { return item.key; })};
    form.dataset.submitting = '';
    resizeReplyComposer();
    api('/api/v1/community/posts/' + encodeURIComponent(state.currentPost.key) + '/contributions', jsonOptions('POST', payload, stableCommandKey(payload, 'reply', state.currentPost.key + ':' + (state.replyParentKey || 'top-level'))))
      .then(function () {
        var usedDraftKey = replyDraftStorageKey(state.currentPost.key, state.replyParentKey);
        form.reset();
        if (replyVoiceController) replyVoiceController.discard(false);
        if (usedDraftKey) {
          try { localStorage.removeItem(usedDraftKey); } catch (ignoreReplyDraftCleanup) {}
        }
        if (replyCommandStorageKey) {
          try { localStorage.removeItem(replyCommandStorageKey); } catch (ignoreReplyCommand) {}
        }
        state.replyParentKey = null;
        state.replyDraftTargetKey = null;
        state.replyAttachments = [];
        state.replyCommandKey = null;
        state.replyPayloadFingerprint = null;
        renderReplyUploads();
        replyDraftStatus(false);
        showToast(app.dataset.preview === 'true' ? 'Reply added to this local preview only.' : 'Reply published.');
        reloadConversation();
        loadFeed(false);
      }).catch(function (error) {
        var retryHint = error.retryable === false ? '' : ' You can try again without creating a duplicate.';
        showToast(error.message + retryHint, true);
      }).finally(function () {
        form.removeAttribute('data-submitting');
        resizeReplyComposer();
      });
  }

  function updatePrimaryResponseControls(post, intention) {
    post.viewer = post.viewer || {};
    post.viewer.response = intention;
    app.querySelectorAll('[data-primary-response-control]').forEach(function (wrapper) {
      var card = wrapper.closest('[data-post-key]');
      if (!card || card.dataset.postKey !== post.key) return;
      var trigger = wrapper.querySelector('[data-primary-response-trigger]');
      if (trigger) setRespondControl(trigger, intention);
      wrapper.querySelectorAll('[data-action="primary-response"]').forEach(function (choice) {
        choice.setAttribute('aria-pressed', choice.dataset.response === intention ? 'true' : 'false');
      });
    });
  }

  function performPrimaryResponse(wrapper, post, intention) {
    if (!post) return;
    var removing = Boolean(post.viewer && post.viewer.response === intention);
    var choices = Array.from(wrapper.querySelectorAll('[data-action="primary-response"]'));
    if (post.demo) {
      updatePrimaryResponseControls(post, removing ? null : intention);
      closePrimaryResponsePicker(wrapper, true);
      showToast(removing ? 'Demo response removed from this tab.' : 'Demo response selected only in this tab.');
      return;
    }
    choices.forEach(function (choice) { choice.disabled = true; });
    api(
      '/api/v1/community/posts/' + encodeURIComponent(post.key) + '/response',
      jsonOptions(removing ? 'DELETE' : 'PUT', removing ? {} : {intention: intention})
    ).then(function () {
      updatePrimaryResponseControls(post, removing ? null : intention);
      closePrimaryResponsePicker(wrapper, true);
      showToast(removing ? 'Response removed.' : 'Response saved privately.');
    }).catch(function (error) {
      showToast(error.message, true);
    }).finally(function () {
      choices.forEach(function (choice) { choice.disabled = false; });
    });
  }

  function deletePost(postKey, revision) {
    if (!window.confirm('Remove this public post? Its public link and attachments will stop working immediately.')) return;
    api('/api/v1/community/posts/' + encodeURIComponent(postKey), jsonOptions('DELETE', {expected_revision: revision}))
      .then(function () { showToast('Post removed from public view.'); state.cursor = null; loadFeed(false); if (conversation.open) conversation.close(); })
      .catch(function (error) { showToast(error.message, true); });
  }

  function copyPermalink(path) {
    var value = new URL(path, window.location.origin).href;
    var operation;
    if (navigator.clipboard && window.isSecureContext) {
      operation = navigator.clipboard.writeText(value);
    } else {
      operation = new Promise(function (resolve, reject) {
        var field = document.createElement('textarea');
        field.value = value;
        field.setAttribute('readonly', '');
        field.className = 'cv1-visually-hidden';
        document.body.appendChild(field);
        field.select();
        var copied = document.execCommand('copy');
        field.remove();
        if (copied) resolve(); else reject(new Error('copy unavailable'));
      });
    }
    operation.then(function () { showToast('Public link copied.'); })
      .catch(function () { showToast('The public link could not be copied.', true); });
  }

  function pushSheetHistory(sheet) {
    var nextState = Object.assign({}, history.state || {}, {communitySheet: sheet});
    history.pushState(nextState, '', location.href);
    state.sheetHistory = sheet;
  }

  function openActivity(trigger, pushHistory) {
    if (activityDialog.open) return;
    state.activityReturnFocus = trigger || document.activeElement;
    activityDialog.showModal();
    if (pushHistory !== false) pushSheetHistory('activity');
  }

  function closeActivity(restoreFocus, consumeHistory) {
    if (!restoreFocus) state.activityReturnFocus = null;
    if (consumeHistory === false) state.sheetHistory = null;
    if (consumeHistory !== false && state.sheetHistory === 'activity' && history.state && history.state.communitySheet === 'activity') {
      state.sheetHistoryClosing = true;
      state.sheetHistory = null;
      if (activityDialog.open) activityDialog.close();
      history.back();
      return;
    }
    if (activityDialog.open) activityDialog.close();
  }

  function openCatchup(trigger, pushHistory) {
    if (catchupDialog.open) return;
    state.catchupReturnFocus = trigger || document.activeElement;
    catchupDialog.showModal();
    if (pushHistory !== false) pushSheetHistory('catchup');
  }

  function closeCatchup(restoreFocus, consumeHistory) {
    if (!restoreFocus) state.catchupReturnFocus = null;
    if (consumeHistory === false) state.sheetHistory = null;
    if (consumeHistory !== false && state.sheetHistory === 'catchup' && history.state && history.state.communitySheet === 'catchup') {
      state.sheetHistoryClosing = true;
      state.sheetHistory = null;
      if (catchupDialog.open) catchupDialog.close();
      history.back();
      return;
    }
    if (catchupDialog.open) catchupDialog.close();
  }

  function closePostMenus(except) {
    app.querySelectorAll('.cv1-card-owner-actions').forEach(function (menu) {
      if (menu === except) return;
      menu.hidden = true;
      var trigger = menu.parentElement.querySelector('[data-action="menu"]');
      if (trigger) trigger.setAttribute('aria-expanded', 'false');
    });
  }

  function closeContributionMenus(except) {
    app.querySelectorAll('details.cv1-contribution-owner-controls[open]').forEach(function (menu) {
      if (menu !== except) menu.open = false;
    });
  }

  function handlePostMenuKeydown(event) {
    var trigger = event.target.closest('[data-action="menu"]');
    if (trigger && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) {
      event.preventDefault();
      var triggerMenu = trigger.parentElement.querySelector('.cv1-card-owner-actions');
      closePostMenus(triggerMenu);
      triggerMenu.hidden = false;
      trigger.setAttribute('aria-expanded', 'true');
      var triggerItems = Array.from(triggerMenu.querySelectorAll('[role="menuitem"]'));
      triggerItems[event.key === 'ArrowUp' ? triggerItems.length - 1 : 0].focus();
      return;
    }
    var menu = event.target.closest('[role="menu"]');
    if (!menu) return;
    var items = Array.from(menu.querySelectorAll('[role="menuitem"]'));
    var index = items.indexOf(event.target);
    if (event.key === 'Escape') {
      event.preventDefault();
      menu.hidden = true;
      var menuTrigger = menu.parentElement.querySelector('[data-action="menu"]');
      menuTrigger.setAttribute('aria-expanded', 'false');
      menuTrigger.focus();
    }
    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && index >= 0) {
      event.preventDefault();
      var direction = event.key === 'ArrowDown' ? 1 : -1;
      items[(index + direction + items.length) % items.length].focus();
    }
  }

  function beginContributionEdit(action) {
    var returnFocus = action.closest('details') && action.closest('details').querySelector('summary');
    var node = action.closest('.cv1-contribution') || conversationBody.querySelector('.cv1-contribution[data-contribution-key="' + CSS.escape(action.dataset.key) + '"]');
    var body = node && node.querySelector('.cv1-contribution-body');
    if (!node || !body || node.querySelector('.cv1-inline-edit')) return;
    var form = el('form', 'cv1-inline-edit');
    var label = el('label', 'cv1-visually-hidden', 'Edit reply');
    var input = el('textarea');
    input.name = 'body';
    input.maxLength = 2000;
    input.required = true;
    input.rows = 4;
    input.value = body.textContent;
    label.htmlFor = 'cv1-inline-edit-' + action.dataset.key;
    input.id = label.htmlFor;
    form.appendChild(label);
    form.appendChild(input);
    var controls = el('div', 'cv1-inline-edit-actions');
    controls.appendChild(button('Cancel', 'cancel-inline-edit', 'cv1-secondary'));
    var save = el('button', 'cv1-primary', 'Save changes');
    save.type = 'submit';
    controls.appendChild(save);
    form.appendChild(controls);
    body.hidden = true;
    node.insertBefore(form, body.nextSibling);
    input.focus();
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      save.disabled = true;
      api('/api/v1/community/contributions/' + action.dataset.key, jsonOptions('PATCH', {body: input.value, expected_revision: action.dataset.revision}))
        .then(function () { showToast('Reply updated.'); reloadConversation(); })
        .catch(function (error) { showToast(error.message, true); save.disabled = false; });
    });
    form.querySelector('[data-action="cancel-inline-edit"]').addEventListener('click', function () {
      form.remove();
      body.hidden = false;
      if (returnFocus && returnFocus.isConnected) returnFocus.focus();
      else node.focus();
    });
  }

  feedList.addEventListener('click', function (event) {
    var actionNode = event.target.closest('[data-action]');
    if (!actionNode) return;
    var card = actionNode.closest('[data-post-key]');
    var postKey = actionNode.dataset.postKey || (card && card.dataset.postKey);
    var post = card && card._communityPost;
    var action = actionNode.dataset.action;
    if (action === 'conversation') {
      event.preventDefault();
      if (post) state.currentPost = post;
      openConversation(postKey, true, null);
    }
    if (action === 'select-contribution') {
      if (post) state.currentPost = post;
      openConversation(postKey, true, actionNode.dataset.contributionKey);
    }
    if (action === 'respond') {
      var primaryResponseControl = actionNode.closest('[data-primary-response-control]');
      if (primaryResponseControl) {
        event.preventDefault();
        openPrimaryResponsePicker(primaryResponseControl);
      }
    }
    if (action === 'primary-response') {
      event.preventDefault();
      performPrimaryResponse(actionNode.closest('[data-primary-response-control]'), post, actionNode.dataset.response);
    }
    if (action === 'write') openComposer();
    if (action === 'retry-feed') loadFeed(actionNode.dataset.append === 'true');
    if (action === 'retry-search') search(state.lastSearch);
    if (action === 'back-to-feed') backToFeed();
    if (action === 'shelf-previous') {
      var previousShelf = actionNode.closest('[data-conversation-shelf]');
      var previousTrack = previousShelf.querySelector('[data-conversation-shelf-track]');
      previousTrack.scrollBy({left: -Math.max(180, previousTrack.clientWidth * 0.75), behavior: motionBehavior()});
      window.setTimeout(function () { updateShelfControls(previousShelf); }, motionDelay());
    }
    if (action === 'shelf-next') advanceShelf(actionNode.closest('[data-conversation-shelf]'));
    if (action === 'menu') {
      var menu = actionNode.parentElement.querySelector('.cv1-card-owner-actions');
      var willOpen = menu.hidden;
      closePostMenus(menu);
      menu.hidden = !willOpen;
      actionNode.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      if (willOpen) menu.querySelector('[role="menuitem"]').focus();
    }
    if (action === 'edit-post') { closePostMenus(); openEdit(card._communityPost); }
    if (action === 'copy-link') { closePostMenus(); copyPermalink(actionNode.dataset.permalink); }
    if (action === 'delete-post') { closePostMenus(); deletePost(postKey, card._communityPost.revision); }
  });

  feedList.addEventListener('keydown', handlePostMenuKeydown);
  conversation.addEventListener('keydown', handlePostMenuKeydown);

  app.addEventListener('click', function (event) {
    if (!event.target.closest('[data-primary-response-control]')) {
      app.querySelectorAll('[data-primary-response-control]').forEach(function (wrapper) {
        closePrimaryResponsePicker(wrapper, false);
      });
    }
    var appBackToFeed = event.target.closest('[data-action="back-to-feed"]');
    if (appBackToFeed && !feedList.contains(appBackToFeed)) backToFeed();
    var demoTopVoice = event.target.closest('[data-demo-top-voice]');
    if (demoTopVoice) {
      openDemoComposer(true);
      return;
    }
    if (event.target.closest('[data-open-demo-composer]')) {
      openDemoComposer(false);
      return;
    }
    if (event.target.closest('[data-close-demo-composer]')) {
      closeDemoComposer();
      return;
    }
    var topVoice = event.target.closest('[data-top-voice]');
    if (topVoice) {
      openComposer('post', null, false);
      window.setTimeout(function () {
        if (composerVoiceController) composerVoiceController.start();
      }, 0);
      return;
    }
    if (event.target.closest('[data-video-unavailable]')) {
      showToast('Video attachments are not available in this owner pilot.');
      return;
    }
    if (event.target.closest('[data-public-audio-unavailable]')) {
      showToast('Public audio attachments are not available in this owner pilot.');
      return;
    }
    var opener = event.target.closest('[data-open-composer]');
    if (opener && catchupDialog.contains(opener) && catchupDialog.open) {
      var openerIntent = opener.dataset.intent;
      var openerSpark = opener.dataset.sparkPrompt;
      closeCatchup(false);
      window.setTimeout(function () { openComposer(openerIntent, openerSpark, false); }, 0);
    } else if (opener) {
      openComposer(opener.dataset.intent, opener.dataset.sparkPrompt, opener.hasAttribute('data-focus-audience'));
    }
    if (event.target.closest('[data-close-composer]')) closeComposer();
    if (event.target.closest('[data-cancel-publication]')) closePublicConfirmation();
    if (event.target.closest('[data-confirm-publication]')) confirmPublicPublication();
    if (event.target.closest('[data-remove-spark]')) {
      state.sparkPrompt = null;
      app.querySelector('[data-spark-context]').hidden = true;
      app.querySelector('[data-composer-body-label]').textContent = 'What’s on your mind?';
    }
    if (event.target.closest('[data-dismiss-publication-banner]')) publicationBanner.hidden = true;
    var catchupOpener = event.target.closest('[data-open-catchup]');
    if (catchupOpener) openCatchup(catchupOpener);
    if (event.target.closest('[data-close-catchup]')) closeCatchup(true);
    if (event.target.closest('[data-catchup-to-feed]')) {
      closeCatchup(false);
      feedList.scrollIntoView({block: 'start'});
      searchInput.focus({preventScroll: true});
    }
    var activityOpener = event.target.closest('[data-open-activity]');
    if (activityOpener && catchupDialog.contains(activityOpener) && catchupDialog.open) {
      var catchupReturn = state.catchupReturnFocus;
      closeCatchup(false, false);
      history.replaceState(Object.assign({}, history.state || {}, {communitySheet: 'activity'}), '', location.href);
      state.sheetHistory = 'activity';
      openActivity(catchupReturn, false);
    } else if (activityOpener) {
      openActivity(activityOpener);
    }
    if (event.target.closest('[data-close-activity]')) closeActivity(true);
    if (event.target.closest('[data-activity-to-feed]')) {
      closeActivity(false);
      feedList.scrollIntoView({block: 'start'});
      searchInput.focus({preventScroll: true});
    }
  });

  function closeConversation() {
    if (replyVoiceController) replyVoiceController.discard(false);
    if (state.conversationPushed) {
      state.conversationPushed = false;
      history.back();
      return;
    }
    if (conversation.open) conversation.close();
  }

  function restoreConversationContext() {
    var context = state.conversationReturn;
    state.conversationReturn = null;
    if (!context) return;
    if (context.shelfTrack && context.shelfTrack.isConnected && context.shelfScrollLeft !== null) {
      context.shelfTrack.scrollLeft = context.shelfScrollLeft;
    }
    window.scrollTo({top: context.scrollY, behavior: 'auto'});
    if (context.focusNode && context.focusNode.isConnected) context.focusNode.focus({preventScroll: true});
  }

  app.querySelector('[data-close-conversation]').addEventListener('click', closeConversation);
  if (replyForm) replyForm.addEventListener('submit', sendReply);
  conversation.addEventListener('click', function (event) {
    if (event.target === conversation) {
      closeConversation();
      return;
    }
    var contributionSummary = event.target.closest('.cv1-contribution-owner-controls > summary');
    if (contributionSummary) closeContributionMenus(contributionSummary.parentElement);
    var action = event.target.closest('[data-action]');
    if (!action) return;
    if (action.dataset.action === 'menu') {
      var postMenu = action.parentElement.querySelector('.cv1-card-owner-actions');
      var willOpen = postMenu.hidden;
      closePostMenus(postMenu);
      postMenu.hidden = !willOpen;
      action.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      if (willOpen) postMenu.querySelector('[role="menuitem"]').focus();
    }
    if (action.dataset.action === 'edit-post') {
      closePostMenus();
      openEdit(conversationHeaderActions._communityPost || state.currentPost);
    }
    if (action.dataset.action === 'copy-link') {
      closePostMenus();
      copyPermalink(action.dataset.permalink);
    }
    if (action.dataset.action === 'delete-post') {
      closePostMenus();
      var conversationPost = conversationHeaderActions._communityPost || state.currentPost;
      if (conversationPost) deletePost(conversationPost.key, conversationPost.revision);
    }
    if (action.dataset.action === 'close-conversation') closeConversation();
    if (action.dataset.action === 'respond') {
      var conversationResponseControl = action.closest('[data-primary-response-control]');
      if (conversationResponseControl) openPrimaryResponsePicker(conversationResponseControl);
    }
    if (action.dataset.action === 'primary-response') {
      var responseWrapper = action.closest('[data-primary-response-control]');
      var responseCard = action.closest('[data-post-key]');
      if (responseWrapper && responseCard && responseCard._communityPost) {
        performPrimaryResponse(responseWrapper, responseCard._communityPost, action.dataset.response);
      }
    }
    if (action.dataset.action === 'view-all-contributions') showFullConversation(false);
    if (action.dataset.action === 'view-original') showFullConversation(true);
    if (action.dataset.action === 'load-earlier') loadEarlierContributions(action);
    if (action.dataset.action === 'expand-root') {
      var rootBody = conversationBody.querySelector('#' + CSS.escape(action.getAttribute('aria-controls')));
      var expanded = action.getAttribute('aria-expanded') === 'true';
      if (rootBody) rootBody.toggleAttribute('data-expanded', !expanded);
      action.setAttribute('aria-expanded', expanded ? 'false' : 'true');
      action.textContent = expanded ? 'Show more' : 'Show less';
    }
    if (action.dataset.action === 'reply-to') {
      var replyTarget = findContribution(action.dataset.key);
      targetReply(replyTarget);
    }
    if (action.dataset.action === 'edit-contribution') {
      var editOverflow = action.closest('details');
      if (editOverflow) editOverflow.open = false;
      beginContributionEdit(action);
    }
    if (action.dataset.action === 'delete-contribution' && window.confirm('Remove this reply from public view?')) {
      var deleteOverflow = action.closest('details');
      if (deleteOverflow) deleteOverflow.open = false;
      api('/api/v1/community/contributions/' + action.dataset.key, jsonOptions('DELETE', {expected_revision: action.dataset.revision}))
        .then(function () { showToast('Reply removed.'); reloadConversation(); })
        .catch(function (error) { showToast(error.message, true); });
    }
  });

  setupDemoComposer();

  if (owner) {
    setupComposerVoiceController();
    setupReplyVoiceController();
    composerForm.addEventListener('submit', publish);
    formField(composerForm, 'body').addEventListener('input', function () { updateCount(); saveDraft(); });
    formField(composerForm, 'audience').addEventListener('change', updatePublishState);
    composerForm.querySelectorAll('[name="intent"]').forEach(function (control) { control.addEventListener('change', saveDraft); });
    formField(composerForm, 'response_posture').addEventListener('change', saveDraft);
    app.querySelector('[data-attachment-input]').addEventListener('change', function (event) { uploadFile(event.target.files[0], state.attachments, renderUploads); event.target.value = ''; });
    app.querySelector('[data-photo-attachment-input]').addEventListener('change', function (event) { uploadFile(event.target.files[0], state.attachments, renderUploads); event.target.value = ''; });
    app.querySelector('[data-attachment-list]').addEventListener('click', function (event) {
      var control = event.target.closest('[data-action]');
      if (!control) return;
      if (control.dataset.action === 'remove-upload') removeUpload(state.attachments, control.dataset.uploadId, renderUploads, false);
      if (control.dataset.action === 'retry-upload') removeUpload(state.attachments, control.dataset.uploadId, renderUploads, true);
    });
    app.querySelector('[data-reply-attachment-input]').addEventListener('change', function (event) { uploadFile(event.target.files[0], state.replyAttachments, renderReplyUploads); event.target.value = ''; });
    app.querySelector('[data-reply-photo-input]').addEventListener('change', function (event) { uploadFile(event.target.files[0], state.replyAttachments, renderReplyUploads); event.target.value = ''; });
    app.querySelector('[data-reply-attachment-list]').addEventListener('click', function (event) {
      var control = event.target.closest('[data-action]');
      if (!control) return;
      if (control.dataset.action === 'remove-reply-upload') removeUpload(state.replyAttachments, control.dataset.uploadId, renderReplyUploads, false);
      if (control.dataset.action === 'retry-reply-upload') removeUpload(state.replyAttachments, control.dataset.uploadId, renderReplyUploads, true);
    });
    if (replyForm) {
      formField(replyForm, 'body').addEventListener('input', function () { saveReplyDraft(); resizeReplyComposer(); });
      formField(replyForm, 'body').addEventListener('keydown', function (event) {
        if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && formField(replyForm, 'body').value.trim()) {
          event.preventDefault();
          replyForm.requestSubmit();
        }
      });
    }
  }

  if (composer) composer.addEventListener('close', function () {
    if (composerVoiceController) composerVoiceController.discard(false);
    restoreComposerHome();
  });
  if (demoComposer) demoComposer.addEventListener('close', function () {
    if (demoComposerVoiceController) demoComposerVoiceController.discard(false);
  });
  catchupDialog.addEventListener('close', function () {
    var catchupFocus = state.catchupReturnFocus;
    state.catchupReturnFocus = null;
    if (catchupFocus && catchupFocus.isConnected) catchupFocus.focus({preventScroll: true});
    if (state.sheetHistory === 'catchup' && !state.sheetHistoryClosing && history.state && history.state.communitySheet === 'catchup') {
      state.sheetHistoryClosing = true;
      state.sheetHistory = null;
      history.back();
    }
  });
  activityDialog.addEventListener('close', function () {
    var returnFocus = state.activityReturnFocus;
    state.activityReturnFocus = null;
    if (returnFocus && returnFocus.isConnected) returnFocus.focus({preventScroll: true});
    if (state.sheetHistory === 'activity' && !state.sheetHistoryClosing && history.state && history.state.communitySheet === 'activity') {
      state.sheetHistoryClosing = true;
      state.sheetHistory = null;
      history.back();
    }
  });
  conversation.addEventListener('close', function () {
    if (replyVoiceController) replyVoiceController.discard(false);
    saveReplyDraft();
    state.conversationRequest += 1;
    if (state.conversationPushed) {
      state.conversationPushed = false;
      history.back();
    } else if (location.pathname.indexOf('/the-slate/posts/') === 0) {
      history.replaceState({}, '', '/the-slate');
    }
    state.conversationFocusKey = null;
    state.selectedContribution = null;
    state.selectedAncestors = [];
    restoreConversationContext();
  });
  searchInput.addEventListener('input', function () {
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(function () { search(searchInput.value); }, 350);
  });
  clearSearch.addEventListener('click', backToFeed);
  document.addEventListener('click', function (event) {
    if (!event.target.closest('.cv1-card-owner-controls')) closePostMenus();
    if (!event.target.closest('.cv1-contribution-owner-controls')) closeContributionMenus();
  });
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    var contributionMenu = event.target.closest('details.cv1-contribution-owner-controls[open]');
    if (!contributionMenu) return;
    event.preventDefault();
    contributionMenu.open = false;
    contributionMenu.querySelector('summary').focus();
  });
  loadMore.addEventListener('click', function () { loadFeed(true); });
  app.querySelector('[data-search-questions]').addEventListener('click', function () { searchInput.focus(); showToast('Search published questions by topic.'); });
  window.addEventListener('popstate', function () {
    if (state.sheetHistoryClosing) {
      state.sheetHistoryClosing = false;
      return;
    }
    if (catchupDialog.open) {
      state.sheetHistory = null;
      catchupDialog.close();
      return;
    }
    if (activityDialog.open) {
      state.sheetHistory = null;
      activityDialog.close();
      return;
    }
    if (location.pathname === '/the-slate' && conversation.open) {
      state.conversationPushed = false;
      conversation.close();
      return;
    }
    var deepLink = location.pathname.match(/^\/the-slate\/posts\/([^/]+)(?:\/contributions\/([^/]+))?\/?$/);
    if (deepLink) openConversation(decodeURIComponent(deepLink[1]), false, deepLink[2] ? decodeURIComponent(deepLink[2]) : null);
  });
  window.addEventListener('pagehide', function () {
    clearDemoAttachments();
    disposeCommunityVoiceControllers();
  });

  loadFeed(false);
  if (app.dataset.postKey) openConversation(app.dataset.postKey, false, app.dataset.contributionKey || null);
}());
