/**
 * Pure VTX MIDI codecs. No devices, filesystem, network, timers, or transport.
 * Source: VOX Valvetronix X MIDI Implementation v1.0 (2015-07-31), pp. 1–17.
 * https://voxamps.com/wp-content/uploads/2019/07/VTX_Midi_Implementation.pdf
 * Tested offline only. These functions do not establish hardware compatibility.
 */
export const HEADER = Object.freeze([0xf0, 0x42, 0x30, 0x00, 0x01, 0x34]);
export const MODE = Object.freeze({ USER: 0, PRESET: 1, MANUAL: 2 });
export const BANK = Object.freeze({ USER: 0, PRESET: 1 });
export const RAW_PROGRAM_LENGTH = 62;
export const PACKED_PROGRAM_LENGTH = 71;

function integer(value, min, max, label) {
  if (!Number.isInteger(value) || value < min || value > max) {
    throw new RangeError(`${label} must be an integer in ${min}..${max}`);
  }
  return value;
}

function bytes(input, label = 'bytes') {
  if (!(input instanceof Uint8Array) && !Array.isArray(input)) {
    throw new TypeError(`${label} must be a Uint8Array or array of bytes`);
  }
  for (const value of input) integer(value, 0, 255, label);
  return Uint8Array.from(input);
}

function exact(input, length, label) {
  const out = bytes(input, label);
  if (out.length !== length) throw new RangeError(`${label} requires ${length} bytes, got ${out.length}`);
  return out;
}

function program(input) { return exact(input, RAW_PROGRAM_LENGTH, 'raw program'); }
function frame(fn, payload = []) { return Uint8Array.from([...HEADER, fn, ...payload, 0xf7]); }
function userSlot(value) { return integer(value, 0, 7, 'user program'); }
function customIndex(value) { return integer(value, 0, 3, 'custom index'); }

function bankAndSlot(bank, slot) {
  integer(bank, 0, 1, 'bank');
  integer(slot, 0, bank === BANK.USER ? 7 : 59, 'program');
  return [bank, slot];
}

function modeAndSlot(mode, slot) {
  integer(mode, 0, 2, 'mode');
  // Manual's program field is six bits; the document gives no narrower range.
  integer(slot, 0, mode === MODE.USER ? 7 : mode === MODE.PRESET ? 59 : 63, 'program');
  return [mode, slot];
}

/** Convert arbitrary 8-bit data to Korg's group-of-seven MIDI-safe encoding. */
export function pack7bit(input) {
  const raw = bytes(input);
  const out = new Uint8Array(raw.length + Math.ceil(raw.length / 7));
  let dest = 0;
  for (let offset = 0; offset < raw.length; offset += 7) {
    const count = Math.min(7, raw.length - offset);
    const prefix = dest++;
    for (let j = 0; j < count; j++) {
      out[prefix] |= ((raw[offset + j] >>> 7) & 1) << j;
      out[dest++] = raw[offset + j] & 0x7f;
    }
  }
  return out;
}

/** Decode exactly rawLength bytes, rejecting high bits and noncanonical padding. */
export function unpack7bit(input, rawLength) {
  integer(rawLength, 0, 0x1000000, 'rawLength');
  const packed = exact(input, rawLength + Math.ceil(rawLength / 7), 'packed data');
  for (const value of packed) integer(value, 0, 127, 'packed byte');
  const out = new Uint8Array(rawLength);
  let src = 0;
  for (let offset = 0; offset < rawLength; offset += 7) {
    const count = Math.min(7, rawLength - offset);
    const prefix = packed[src++];
    if (prefix >>> count) throw new RangeError('nonzero unused high-bit flags in final group');
    for (let j = 0; j < count; j++) out[offset + j] = packed[src++] | (((prefix >>> j) & 1) << 7);
  }
  return out;
}

export function inquiry(deviceId = 0x7f) {
  if (deviceId !== 0 && deviceId !== 0x7f) throw new RangeError('inquiry deviceId must be 0 or 127');
  return Uint8Array.of(0xf0, 0x7e, deviceId, 0x06, 0x01, 0xf7);
}
export function getMode() { return frame(0x12); }
export function getCurrentProgram() { return frame(0x10); }
export function getProgram(bank, slot) { return frame(0x1c, bankAndSlot(bank, slot)); }
export function getCustomData(index) { return frame(0x31, [0, customIndex(index)]); }
export function setMode(mode, slot) { return frame(0x4e, modeAndSlot(mode, slot)); }
/** Prepare an edit-buffer update. This does not save into a user memory. */
export function currentProgramDump(raw) { return frame(0x40, pack7bit(program(raw))); }
/** Prepare a direct internal-memory write to a user slot; no preset writes. */
export function programDump(slot, raw) { return frame(0x4c, [0, userSlot(slot), ...pack7bit(program(raw))]); }
/** Prepare a custom-slot internal-memory write. */
export function customDataDump(index, raw) { return frame(0x65, [0, customIndex(index), ...pack7bit(program(raw))]); }
/** Prepare a request to persist the current buffer in one user slot. */
export function writeCurrentProgram(slot) { return frame(0x11, [0, userSlot(slot)]); }

const names = ['gain', 'treble', 'middle', 'bass', 'volume', 'presenceOrTone', 'resonance',
  'brightCap', 'lowCut', 'midBoost', 'bias', 'powerClass'];

function field(key, offset, width, min, max, bit = undefined) {
  return { key, offset, width, min, max, ...(bit === undefined ? {} : { bit }) };
}

/** Model context is mandatory for the two effect groups, whose spans vary. */
export function parameterInfo(id, subId, context = {}) {
  integer(id, 0, 127, 'parameter ID');
  integer(subId, 0, 127, 'parameter sub-ID');
  if (id === 0 && subId <= 15) return field(`name[${subId}]`, subId, 1, 32, 126);
  if (id === 1 && subId === 0) return field('noiseReduction', 16, 1, 0, 100);
  if (id === 2 && [1, 2, 4].includes(subId)) return field('effectEnabled', 17, 1, 0, 1, subId);
  if (id === 3) {
    const models = { 0: ['ampModel', 18, 19], 1: ['pedal1Model', 31, 9],
      2: ['pedal2Model', 39, 6], 4: ['reverbModel', 55, 3] };
    if (models[subId]) {
      const [key, offset, max] = models[subId];
      return field(key, offset, 1, 0, max);
    }
  }
  if (id === 4 && subId <= 11) return field(names[subId], 19 + subId, 1, 0,
    subId <= 6 ? 100 : subId === 10 ? 2 : 1);
  if (id === 8 && subId <= 4) return field(
    ['reverbMix', 'reverbTime', 'reverbPreDelay', 'reverbLowDamp', 'reverbHighDamp'][subId],
    56 + subId, 1, 0, subId === 2 ? 70 : 100);
  if (id === 5 || id === 6) {
    const model = id === 5 ? context.pedal1Model : context.pedal2Model;
    integer(model, 0, id === 5 ? 9 : 6, id === 5 ? 'context.pedal1Model' : 'context.pedal2Model');
    let fields;
    if (id === 5) {
      fields = model === 0
        ? [['sensitivity', 0, 100], ['level', 0, 100], ['attack', 0, 100], ['voice', 0, 2]]
        : model === 1
          ? [['speed', 100, 10000], ['depth', 0, 100], ['manual', 0, 100], ['mix', 0, 100], ['lowCut', 0, 1], ['highCut', 0, 1]]
          : [['drive', 0, 100], ['tone', 0, 100], ['level', 0, 100], ['treble', 0, 100], ['middle', 0, 100], ['bass', 0, 100]];
    } else {
      fields = model === 0
        ? [['speed', 100, 5000], ['depth', 0, 100], ['manual', 0, 100], ['lowCut', 0, 1], ['highCut', 0, 1], ['resonance', 0, 100]]
        : model <= 3
          ? [['speed', 100, 10000], ['resonance', 0, 100], ['manual', 0, 100], ['depth', 0, 100]]
          : model === 4
            ? [['speed', 1650, 10000], ['depth', 0, 100], ['duty', 0, 100], ['shape', 0, 100], ['level', 0, 100]]
            : [['time', 30, 1200], ['level', 0, 100], ['feedback', 0, 100], ['tone', 0, 100], ['modSpeed', 0, 100], ['modDepth', 0, 100]];
    }
    if (subId < fields.length) {
      const [key, min, max] = fields[subId];
      const base = id === 5 ? 32 : 40;
      return field(key, base + (subId === 0 ? 0 : subId + 1), subId === 0 ? 2 : 1, min, max);
    }
  }
  throw new RangeError(`unsupported VTX parameter ${id.toString(16)}/${subId.toString(16)}`);
}

export function programContext(raw) {
  const data = program(raw);
  return { pedal1Model: data[31], pedal2Model: data[39] };
}

export function setParameter(id, subId, value, context = {}) {
  const info = parameterInfo(id, subId, context);
  integer(value, info.min, info.max, info.key);
  return frame(0x41, [id, subId, value & 0x7f, value >>> 7]);
}

/** Read one documented field; throws for reserved/unknown parameter spans. */
export function getParameter(raw, id, subId) {
  const data = program(raw);
  const info = parameterInfo(id, subId, programContext(data));
  const value = info.bit !== undefined ? (data[info.offset] >>> info.bit) & 1
    : data[info.offset] | (info.width === 2 ? data[info.offset + 1] << 8 : 0);
  return integer(value, info.min, info.max, info.key);
}

/** Return an edited copy; preserves every byte outside the selected field. */
export function withParameter(raw, id, subId, value) {
  const data = program(raw);
  const info = parameterInfo(id, subId, programContext(data));
  integer(value, info.min, info.max, info.key);
  if (info.bit !== undefined) data[info.offset] = (data[info.offset] & ~(1 << info.bit)) | (value << info.bit);
  else {
    data[info.offset] = value & 255;
    if (info.width === 2) data[info.offset + 1] = value >>> 8;
  }
  return data;
}

/**
 * Parse one complete SysEx message, not a stream or USB-MIDI event packet.
 * Requires model context when parsing a pedal parameter-change message.
 * Raw dumps remain lossless opaque 62-byte data; unknown bytes are preserved.
 */
export function parseMessage(input, context = {}) {
  const data = bytes(input, 'SysEx');
  if (data.length < 6 || data[0] !== 0xf0 || data.at(-1) !== 0xf7) {
    throw new RangeError('expected one complete SysEx frame');
  }
  for (const value of data.subarray(1, -1)) integer(value, 0, 127, 'SysEx data byte');
  if (data[1] === 0x7e) {
    if (data.length === 6 && (data[2] === 0 || data[2] === 127) && data[3] === 6 && data[4] === 1) {
      return { type: 'inquiry', deviceId: data[2] };
    }
    const fixed = { 2: 0, 3: 6, 4: 2, 5: 0x42, 6: 0x34, 7: 1, 8: 0, 9: 0, 11: 0, 13: 0 };
    if (data.length !== 15 || Object.entries(fixed).some(([i, value]) => data[i] !== value)) {
      throw new RangeError('not a documented VTX identity reply');
    }
    return { type: 'identity', manufacturer: 0x42, family: [0x34, 1], member: [0, 0], minor: data[10], major: data[12] };
  }
  if (data.length < 8 || HEADER.some((value, i) => data[i] !== value)) throw new RangeError('not a VTX SysEx frame');
  const fn = data[6];
  const payload = data.subarray(7, -1);
  const length = n => { if (payload.length !== n) throw new RangeError(`function 0x${fn.toString(16)} expects ${n} payload bytes`); };
  const reserved = () => { if (payload[0] !== 0) throw new RangeError('reserved byte must be zero'); };
  const answer = (type, fields = {}) => ({ type, function: fn, ...fields });
  switch (fn) {
    case 0x12: length(0); return answer('getMode');
    case 0x10: length(0); return answer('getCurrentProgram');
    case 0x1c:
      length(2); bankAndSlot(payload[0], payload[1]);
      return answer('getProgram', { bank: payload[0], program: payload[1] });
    case 0x31:
      length(2); reserved(); customIndex(payload[1]);
      return answer('getCustomData', { index: payload[1] });
    case 0x11:
      length(2); reserved(); userSlot(payload[1]);
      return answer('writeCurrentProgram', { program: payload[1] });
    case 0x42:
    case 0x4e:
      length(2); modeAndSlot(payload[0], payload[1]);
      return answer(fn === 0x42 ? 'modeState' : 'modeChange', { mode: payload[0], program: payload[1] });
    case 0x41: {
      length(4);
      const [id, subId, low, high] = payload;
      const value = low | (high << 7);
      const info = parameterInfo(id, subId, context);
      integer(value, info.min, info.max, info.key);
      return answer('parameterChange', { id, subId, value });
    }
    case 0x40:
      length(71); return answer('currentProgramDump', { raw: unpack7bit(payload, 62) });
    case 0x4c:
      length(73); bankAndSlot(payload[0], payload[1]);
      return answer('programDump', { bank: payload[0], program: payload[1], raw: unpack7bit(payload.subarray(2), 62) });
    case 0x65:
      length(73); reserved(); customIndex(payload[1]);
      return answer('customDataDump', { index: payload[1], raw: unpack7bit(payload.subarray(2), 62) });
    case 0x23: length(0); return answer('ack');
    case 0x24: length(0); return answer('nak');
    case 0x26: length(0); return answer('formatError');
    case 0x21:
    case 0x22:
      length(2); reserved(); userSlot(payload[1]);
      return answer(fn === 0x21 ? 'writeAck' : 'writeNak', { program: payload[1] });
    default: throw new RangeError(`unsupported VTX function 0x${fn.toString(16)}`);
  }
}
