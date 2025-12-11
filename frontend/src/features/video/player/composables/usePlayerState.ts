import { ref } from 'vue';

export function usePlayerState() {
  const currentTime = ref(0);
  const isPlaying = ref(false);
  const showDanmaku = ref(true);

  const handlePlay = () => {
    isPlaying.value = true;
  };

  const handlePause = () => {
    isPlaying.value = false;
  };

  const handleTimeUpdate = (time: number) => {
    currentTime.value = time;
  };

  return {
    currentTime,
    isPlaying,
    showDanmaku,
    handlePlay,
    handlePause,
    handleTimeUpdate,
  };
}
