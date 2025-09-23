-- CreateTable
CREATE TABLE "music_audio_features" (
    "track_id" INTEGER NOT NULL,
    "danceability" TEXT,
    "loudness" TEXT,
    "acousticness" TEXT,
    "instrumentalness" TEXT,
    "valence" TEXT,
    "energy" TEXT,

    CONSTRAINT "music_audio_features_pkey" PRIMARY KEY ("track_id")
);

-- CreateTable
CREATE TABLE "music_lyrics" (
    "track_id" INTEGER NOT NULL,
    "lyrics" TEXT,

    CONSTRAINT "music_lyrics_pkey" PRIMARY KEY ("track_id")
);

-- CreateTable
CREATE TABLE "music_main" (
    "track_id" INTEGER NOT NULL,
    "artist_name" TEXT,
    "track_name" TEXT,
    "release_date" INTEGER,
    "genre" TEXT,
    "len" TEXT,
    "topic" TEXT,
    "age" TEXT,

    CONSTRAINT "music_main_pkey" PRIMARY KEY ("track_id")
);

-- CreateTable
CREATE TABLE "music_topic_scores" (
    "track_id" INTEGER NOT NULL,
    "dating" TEXT,
    "violence" TEXT,
    "world/life" TEXT,
    "night/time" TEXT,
    "shake the audience" TEXT,
    "family/gospel" TEXT,
    "romantic" TEXT,
    "communication" TEXT,
    "obscene" TEXT,
    "music" TEXT,
    "movement/places" TEXT,
    "light/visual perceptions" TEXT,
    "family/spiritual" TEXT,
    "like/girls" TEXT,
    "sadness" TEXT,
    "feelings" TEXT,

    CONSTRAINT "music_topic_scores_pkey" PRIMARY KEY ("track_id")
);

-- AddForeignKey
ALTER TABLE "music_audio_features" ADD CONSTRAINT "music_audio_features_track_id_fkey" FOREIGN KEY ("track_id") REFERENCES "music_main"("track_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "music_lyrics" ADD CONSTRAINT "music_lyrics_track_id_fkey" FOREIGN KEY ("track_id") REFERENCES "music_main"("track_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "music_topic_scores" ADD CONSTRAINT "music_topic_scores_track_id_fkey" FOREIGN KEY ("track_id") REFERENCES "music_main"("track_id") ON DELETE NO ACTION ON UPDATE NO ACTION;

